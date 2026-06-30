"""Scenario engine for the CypressBit Transportation I-O Modeling Lab.

Orchestrates the full I-O pipeline from ScenarioInput parameters to a
ScenarioResult, and provides helpers for building final demand vectors and
comparing multiple scenarios side-by-side.

Pipeline for a single scenario (Section 8.6 of the build instructions):
    1. Load data via adapter
    2. Apply inflation adjustment
    3. Build Z, x, A, LeontiefModel
    4. Build final demand from project cost mix
    5. Calculate direct, indirect, and (optionally) induced employment
    6. Package results into ScenarioResult
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .coefficients import (
    build_transaction_matrix,
    build_output_vector,
    calculate_direct_requirements,
    calculate_employment_coefficients,
)
from .employment import (
    calculate_direct_indirect_employment,
    calculate_employment,
)
from .leontief import LeontiefModel
from .schemas import ScenarioInput, ScenarioResult


def get_inflation_factor(
    inflation_df: pd.DataFrame,
    base_year: int,
    analysis_year: int,
) -> float:
    """Return the price index ratio for converting base-year dollars to analysis-year dollars.

    Args:
        inflation_df: DataFrame with columns 'year' (int) and 'index_value' (float).
        base_year: Dollar basis year for the spending amount.
        analysis_year: Target year for the analysis.

    Returns:
        index_analysis / index_base.  Returns 1.0 (no adjustment) if either
        year is not found in the index table.
    """
    year_to_index: dict[int, float] = {
        int(row["year"]): float(row["index_value"])
        for _, row in inflation_df.iterrows()
    }
    base = year_to_index.get(base_year)
    analysis = year_to_index.get(analysis_year)
    if base is None or analysis is None:
        return 1.0
    return analysis / base


def build_final_demand_from_cost_mix(
    spending_amount: float,
    improvement_type: str,
    cost_mix_df: pd.DataFrame,
    sector_ids: list[str],
    domestic_adjustment: bool = True,
) -> np.ndarray:
    """Allocate total project spending to I-O sectors using the cost mix table.

    For each sector that appears in the cost mix for the given improvement type:

        f[i] = spending_amount * sector_share_total

    If domestic_adjustment is True, apply a weighted-average import-penetration
    adjustment (prototype — Section 6.4 of the build instructions):

        weighted_ds[i] = sum(share_k * domestic_share_k) / sum(share_k)
        f[i] = spending_amount * sector_share_total * weighted_ds[i]

    Sectors absent from the cost mix receive f[i] = 0.

    Args:
        spending_amount: Total project spending in dollars (after inflation adjustment).
        improvement_type: Project type string, e.g. "pavement", "bridge", "safety".
        cost_mix_df: DataFrame with columns improvement_type, sector_id, share,
            domestic_share.
        sector_ids: Ordered list of sector identifiers that defines the vector
            length and position of each sector.
        domestic_adjustment: Whether to scale f[i] by the sector's weighted
            average domestic share.

    Returns:
        f (n,) float64 array of final demand in dollars, aligned to sector_ids.
    """
    n = len(sector_ids)
    f = np.zeros(n, dtype=np.float64)
    idx = {sid: i for i, sid in enumerate(sector_ids)}

    type_rows = cost_mix_df[cost_mix_df["improvement_type"] == improvement_type]

    for sector_id, group in type_rows.groupby("sector_id", sort=False):
        if sector_id not in idx:
            continue
        i = idx[sector_id]
        total_share = float(group["share"].sum())
        if domestic_adjustment:
            # Weighted average: sum(share_k * ds_k) / sum(share_k)
            weighted_ds = float(
                (group["share"] * group["domestic_share"]).sum()
            ) / total_share
            f[i] = spending_amount * total_share * weighted_ds
        else:
            f[i] = spending_amount * total_share

    return f


def run_scenario(
    scenario_input: ScenarioInput,
    data_adapter=None,
) -> ScenarioResult:
    """Run the full I-O pipeline for one scenario and return a ScenarioResult.

    Args:
        scenario_input: ScenarioInput pydantic model with all parameters.
        data_adapter: Optional data adapter instance.  Defaults to
            SampleDataAdapter if not provided.

    Returns:
        ScenarioResult containing per-sector output and employment arrays plus
        aggregate employment totals.
    """
    # Import here to avoid a circular dependency at module load time.
    from .data_adapters import SampleDataAdapter

    # 1. Resolve adapter
    adapter = data_adapter if data_adapter is not None else SampleDataAdapter()

    # 2. Load all five data frames
    sectors_df = adapter.load_sectors()
    transactions_df = adapter.load_transactions()
    cost_mix_df = adapter.load_cost_mix()
    consumer_df = adapter.load_consumer_spending()
    inflation_df = adapter.load_inflation_index()

    # 3. Inflation factor
    inflation_factor = get_inflation_factor(
        inflation_df, scenario_input.base_year, scenario_input.analysis_year
    )

    # 4. Adjusted spending in dollars
    adjusted_spending = scenario_input.spending_amount * inflation_factor

    # 5. Build Z, x, A, and the Leontief model
    Z = build_transaction_matrix(transactions_df, sectors_df)
    x = build_output_vector(sectors_df)
    A = calculate_direct_requirements(Z, x)
    sector_ids = sectors_df["sector_id"].tolist()
    model = LeontiefModel(A, sector_ids)

    # 6. Employment coefficients aligned to sector order
    emp_coeff_df = calculate_employment_coefficients(sectors_df)
    emp_coeffs_arr = emp_coeff_df["employment_coeff"].to_numpy(dtype=np.float64)

    # 7. Build final demand from cost mix with adjusted spending
    final_demand = build_final_demand_from_cost_mix(
        adjusted_spending,
        scenario_input.improvement_type,
        cost_mix_df,
        sector_ids,
        domestic_adjustment=scenario_input.domestic_adjustment,
    )

    # 8. Direct and indirect output + employment
    direct_output_arr = final_demand.copy()
    indirect_output_arr = model.indirect_output(final_demand)
    direct_emp, indirect_emp = calculate_direct_indirect_employment(
        model, final_demand, emp_coeffs_arr
    )

    # 9. Induced output + employment (simplified prototype — Section 6.3)
    n = model.n_sectors
    if scenario_input.include_induced:
        total_output = model.solve(final_demand)  # direct + indirect output
        wage_shares_arr = sectors_df["wage_share"].to_numpy(dtype=np.float64)

        # Align consumer spending shares to model sector order; unmapped sectors get 0
        consumer_map = dict(zip(consumer_df["sector_id"], consumer_df["share"]))
        consumer_spending_shares = np.array(
            [consumer_map.get(sid, 0.0) for sid in sector_ids], dtype=np.float64
        )

        # Household final demand (Section 6.3)
        labor_income = float(np.dot(total_output, wage_shares_arr))
        household_f = (
            labor_income
            * scenario_input.marginal_consumption_share
            * consumer_spending_shares
        )
        induced_output_arr = model.solve(household_f)
        induced_emp = calculate_employment(induced_output_arr, emp_coeffs_arr)
    else:
        induced_output_arr = np.zeros(n, dtype=np.float64)
        induced_emp = np.zeros(n, dtype=np.float64)

    return ScenarioResult(
        scenario_input=scenario_input,
        sector_ids=sector_ids,
        sector_names=sectors_df["sector_name"].tolist(),
        final_demand=final_demand.tolist(),
        direct_output=direct_output_arr.tolist(),
        indirect_output=indirect_output_arr.tolist(),
        induced_output=induced_output_arr.tolist(),
        direct_employment=direct_emp.tolist(),
        indirect_employment=indirect_emp.tolist(),
        induced_employment=induced_emp.tolist(),
        inflation_adjustment_factor=inflation_factor,
    )


def compare_scenarios(
    scenario_inputs: list[ScenarioInput],
    data_adapter=None,
) -> pd.DataFrame:
    """Run multiple scenarios and return a side-by-side comparison DataFrame.

    Args:
        scenario_inputs: List of ScenarioInput instances to evaluate.
        data_adapter: Optional shared data adapter; defaults to SampleDataAdapter.

    Returns:
        DataFrame with one row per scenario and columns:
            scenario_name, spending_amount, improvement_type, include_induced,
            direct_jobs_fte, indirect_jobs_fte, induced_jobs_fte,
            total_jobs_fte, jobs_per_million.
    """
    rows = []
    for si in scenario_inputs:
        result = run_scenario(si, data_adapter)
        emp = result.employment
        rows.append(
            {
                "scenario_name": si.scenario_name,
                "spending_amount": si.spending_amount,
                "improvement_type": si.improvement_type,
                "include_induced": si.include_induced,
                "direct_jobs_fte": emp.direct_jobs_fte,
                "indirect_jobs_fte": emp.indirect_jobs_fte,
                "induced_jobs_fte": emp.induced_jobs_fte,
                "total_jobs_fte": emp.total_jobs_fte,
                "jobs_per_million": result.jobs_per_million,
            }
        )
    return pd.DataFrame(rows)
