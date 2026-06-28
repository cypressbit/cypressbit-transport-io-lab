"""Data and model validation for the CypressBit Transportation I-O Modeling Lab.

All functions return lists of ValidationIssue so callers can decide whether
to abort on errors, log warnings, or surface issues in the dashboard.
"""

from __future__ import annotations

import math

import pandas as pd

from .schemas import ScenarioResult, ValidationIssue

# Required columns for each data frame — used for null checks.
_SECTORS_REQUIRED = [
    "sector_id",
    "sector_name",
    "bea_code",
    "naics_hint",
    "output_millions",
    "employment_fte",
    "wage_share",
]

_TRANSACTIONS_REQUIRED = [
    "supplier_sector_id",
    "purchaser_sector_id",
    "transaction_millions",
]

_COST_MIX_REQUIRED = [
    "improvement_type",
    "spending_category",
    "sector_id",
    "share",
    "domestic_share",
]

_CONSUMER_REQUIRED = ["sector_id", "share"]

# Tolerance for share-sum checks (covers floating-point rounding in source data).
_SHARE_TOLERANCE = 0.001


# ---------------------------------------------------------------------------
# Individual validators
# ---------------------------------------------------------------------------

def validate_sectors(df: pd.DataFrame) -> list[ValidationIssue]:
    """Validate the sectors DataFrame.

    Checks:
    - All required columns are present.
    - No nulls in required columns.
    - sector_id values are unique.
    - output_millions > 0 for every row.
    - employment_fte >= 0 for every row.
    - wage_share in [0, 1] for every row.
    """
    issues: list[ValidationIssue] = []

    missing = [c for c in _SECTORS_REQUIRED if c not in df.columns]
    if missing:
        issues.append(ValidationIssue(
            issue_type="missing_columns",
            description=f"sectors DataFrame is missing required columns: {missing}",
            severity="error",
        ))
        return issues  # further checks are meaningless without the columns

    for col in _SECTORS_REQUIRED:
        null_count = int(df[col].isna().sum())
        if null_count:
            issues.append(ValidationIssue(
                issue_type="null_values",
                description=f"sectors column '{col}' has {null_count} null value(s)",
                severity="error",
            ))

    dupes = df["sector_id"][df["sector_id"].duplicated()].tolist()
    if dupes:
        issues.append(ValidationIssue(
            issue_type="duplicate_sector_id",
            description=f"Duplicate sector_id values found: {dupes}",
            severity="error",
        ))

    bad_output = df[df["output_millions"] <= 0]["sector_id"].tolist()
    if bad_output:
        issues.append(ValidationIssue(
            issue_type="non_positive_output",
            description=(
                f"output_millions must be > 0; offending sector_id(s): {bad_output}"
            ),
            severity="error",
        ))

    bad_emp = df[df["employment_fte"] < 0]["sector_id"].tolist()
    if bad_emp:
        issues.append(ValidationIssue(
            issue_type="negative_employment",
            description=(
                f"employment_fte must be >= 0; offending sector_id(s): {bad_emp}"
            ),
            severity="error",
        ))

    bad_wage = df[(df["wage_share"] < 0) | (df["wage_share"] > 1)]["sector_id"].tolist()
    if bad_wage:
        issues.append(ValidationIssue(
            issue_type="wage_share_out_of_range",
            description=(
                f"wage_share must be in [0, 1]; offending sector_id(s): {bad_wage}"
            ),
            severity="error",
        ))

    return issues


def validate_transactions(
    df: pd.DataFrame, sectors_df: pd.DataFrame
) -> list[ValidationIssue]:
    """Validate the transactions DataFrame against the known sector list.

    Checks:
    - All required columns are present.
    - No nulls in required columns.
    - All supplier_sector_id values exist in sectors_df.
    - All purchaser_sector_id values exist in sectors_df.
    - transaction_millions >= 0 for every row.
    """
    issues: list[ValidationIssue] = []

    missing = [c for c in _TRANSACTIONS_REQUIRED if c not in df.columns]
    if missing:
        issues.append(ValidationIssue(
            issue_type="missing_columns",
            description=f"transactions DataFrame is missing required columns: {missing}",
            severity="error",
        ))
        return issues

    for col in _TRANSACTIONS_REQUIRED:
        null_count = int(df[col].isna().sum())
        if null_count:
            issues.append(ValidationIssue(
                issue_type="null_values",
                description=f"transactions column '{col}' has {null_count} null value(s)",
                severity="error",
            ))

    known = set(sectors_df["sector_id"].dropna().tolist()) if "sector_id" in sectors_df.columns else set()

    unknown_suppliers = set(df["supplier_sector_id"].dropna()) - known
    if unknown_suppliers:
        issues.append(ValidationIssue(
            issue_type="unknown_supplier_sector_id",
            description=(
                f"supplier_sector_id value(s) not found in sectors: {sorted(unknown_suppliers)}"
            ),
            severity="error",
        ))

    unknown_purchasers = set(df["purchaser_sector_id"].dropna()) - known
    if unknown_purchasers:
        issues.append(ValidationIssue(
            issue_type="unknown_purchaser_sector_id",
            description=(
                f"purchaser_sector_id value(s) not found in sectors: {sorted(unknown_purchasers)}"
            ),
            severity="error",
        ))

    bad_tx = df[df["transaction_millions"] < 0]
    if not bad_tx.empty:
        issues.append(ValidationIssue(
            issue_type="negative_transaction",
            description=(
                f"transaction_millions must be >= 0; {len(bad_tx)} row(s) violate this"
            ),
            severity="error",
        ))

    return issues


def validate_cost_mix(df: pd.DataFrame) -> list[ValidationIssue]:
    """Validate the project cost mix DataFrame.

    Checks:
    - All required columns are present.
    - No nulls in required columns.
    - For each improvement_type, the sum of share equals 1.0 ± 0.001.
    - domestic_share in [0, 1] for every row.
    """
    issues: list[ValidationIssue] = []

    missing = [c for c in _COST_MIX_REQUIRED if c not in df.columns]
    if missing:
        issues.append(ValidationIssue(
            issue_type="missing_columns",
            description=f"cost_mix DataFrame is missing required columns: {missing}",
            severity="error",
        ))
        return issues

    for col in _COST_MIX_REQUIRED:
        null_count = int(df[col].isna().sum())
        if null_count:
            issues.append(ValidationIssue(
                issue_type="null_values",
                description=f"cost_mix column '{col}' has {null_count} null value(s)",
                severity="error",
            ))

    for itype, group in df.groupby("improvement_type"):
        total = float(group["share"].sum())
        if abs(total - 1.0) > _SHARE_TOLERANCE:
            issues.append(ValidationIssue(
                issue_type="share_sum_not_one",
                description=(
                    f"cost_mix shares for improvement_type='{itype}' sum to "
                    f"{total:.6f}, expected 1.0 ± {_SHARE_TOLERANCE}"
                ),
                severity="error",
            ))

    bad_ds = df[(df["domestic_share"] < 0) | (df["domestic_share"] > 1)]
    if not bad_ds.empty:
        issues.append(ValidationIssue(
            issue_type="domestic_share_out_of_range",
            description=(
                f"domestic_share must be in [0, 1]; {len(bad_ds)} row(s) violate this"
            ),
            severity="error",
        ))

    return issues


def validate_consumer_spending(df: pd.DataFrame) -> list[ValidationIssue]:
    """Validate the consumer spending vector DataFrame.

    Checks:
    - Required columns are present.
    - No nulls in required columns.
    - The sum of share equals 1.0 ± 0.001.
    """
    issues: list[ValidationIssue] = []

    missing = [c for c in _CONSUMER_REQUIRED if c not in df.columns]
    if missing:
        issues.append(ValidationIssue(
            issue_type="missing_columns",
            description=f"consumer_spending DataFrame is missing required columns: {missing}",
            severity="error",
        ))
        return issues

    for col in _CONSUMER_REQUIRED:
        null_count = int(df[col].isna().sum())
        if null_count:
            issues.append(ValidationIssue(
                issue_type="null_values",
                description=f"consumer_spending column '{col}' has {null_count} null value(s)",
                severity="error",
            ))

    total = float(df["share"].sum())
    if abs(total - 1.0) > _SHARE_TOLERANCE:
        issues.append(ValidationIssue(
            issue_type="share_sum_not_one",
            description=(
                f"consumer_spending shares sum to {total:.6f}, "
                f"expected 1.0 ± {_SHARE_TOLERANCE}"
            ),
            severity="error",
        ))

    return issues


def validate_scenario_result(result: ScenarioResult) -> list[ValidationIssue]:
    """Validate a completed ScenarioResult for NaN or infinite values.

    Checks the six sector-level effect arrays:
    direct_output, indirect_output, induced_output,
    direct_employment, indirect_employment, induced_employment.
    """
    issues: list[ValidationIssue] = []

    arrays = {
        "direct_output": result.direct_output,
        "indirect_output": result.indirect_output,
        "induced_output": result.induced_output,
        "direct_employment": result.direct_employment,
        "indirect_employment": result.indirect_employment,
        "induced_employment": result.induced_employment,
    }

    for field, values in arrays.items():
        nan_indices = [i for i, v in enumerate(values) if math.isnan(v)]
        inf_indices = [i for i, v in enumerate(values) if math.isinf(v)]

        if nan_indices:
            issues.append(ValidationIssue(
                issue_type="nan_in_result",
                description=(
                    f"ScenarioResult field '{field}' contains NaN at "
                    f"sector indices: {nan_indices}"
                ),
                severity="error",
            ))

        if inf_indices:
            issues.append(ValidationIssue(
                issue_type="infinite_in_result",
                description=(
                    f"ScenarioResult field '{field}' contains infinite value(s) at "
                    f"sector indices: {inf_indices}"
                ),
                severity="error",
            ))

    return issues


# ---------------------------------------------------------------------------
# Aggregate helpers
# ---------------------------------------------------------------------------

def run_all_validations(
    sectors_df: pd.DataFrame,
    transactions_df: pd.DataFrame,
    cost_mix_df: pd.DataFrame,
    consumer_df: pd.DataFrame,
) -> list[ValidationIssue]:
    """Run all four data validators and return the combined issue list."""
    issues: list[ValidationIssue] = []
    issues.extend(validate_sectors(sectors_df))
    issues.extend(validate_transactions(transactions_df, sectors_df))
    issues.extend(validate_cost_mix(cost_mix_df))
    issues.extend(validate_consumer_spending(consumer_df))
    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    """Return True if any ValidationIssue has severity='error'."""
    return any(issue.severity == "error" for issue in issues)
