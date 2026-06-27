"""Pydantic v2 data models for the CypressBit Transportation I-O Modeling Lab.

These models define the canonical data contracts used across all modules.
Using Pydantic ensures that invalid data is caught at the boundary rather than
propagating silently into numerical calculations.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Sector(BaseModel):
    """A single industry sector in the I-O model.

    Corresponds to one row in data/sample/sectors.csv.
    """

    sector_id: str = Field(description="Unique sector identifier, e.g. 'S001'")
    sector_name: str
    bea_code: str = Field(description="BEA industry code or synthetic placeholder")
    naics_hint: str = Field(description="NAICS code hint or range")
    output_millions: float = Field(gt=0, description="Total gross output in millions of dollars")
    employment_fte: float = Field(ge=0, description="Total FTE employment")
    wage_share: float = Field(ge=0, le=1, description="Labor compensation as a share of output")
    notes: str = ""

    @property
    def employment_coeff(self) -> float:
        """FTE jobs per dollar of gross output.

        Derived from: employment_fte / (output_millions * 1_000_000)
        """
        return self.employment_fte / (self.output_millions * 1_000_000)

    @property
    def jobs_per_million(self) -> float:
        """FTE jobs per million dollars of gross output.

        Derived from: employment_fte / output_millions
        """
        return self.employment_fte / self.output_millions


class ProjectCostItem(BaseModel):
    """One spending-category row in the project cost mix.

    Corresponds to one row in data/sample/project_cost_mix.csv.
    The share values for a given improvement_type must sum to 1.0 across all
    rows for that type; this invariant is checked in validation.py.
    """

    improvement_type: str = Field(description="e.g. 'pavement', 'bridge', 'safety'")
    spending_category: str = Field(description="e.g. 'asphalt', 'engineering'")
    sector_id: str = Field(description="Sector that receives this spending share")
    share: float = Field(ge=0, le=1, description="Fraction of total project spending")
    domestic_share: float = Field(
        ge=0,
        le=1,
        description="Fraction of this category's spending that goes to domestic production",
    )
    notes: str = ""


class ScenarioInput(BaseModel):
    """Parameters that define a single scenario run.

    All fields have defaults that reproduce the canonical example scenario
    from Section 16 of the build instructions.
    """

    spending_amount: float = Field(gt=0, description="Total project spending in dollars")
    base_year: int = Field(default=2022, ge=2000, le=2100, description="Dollar basis year")
    analysis_year: int = Field(default=2026, ge=2000, le=2100, description="Target analysis year")
    improvement_type: str = Field(
        default="pavement",
        description="Project improvement type: pavement, bridge, or safety",
    )
    include_induced: bool = Field(
        default=True,
        description="Whether to compute simplified induced employment effects",
    )
    domestic_adjustment: bool = Field(
        default=True,
        description="Whether to apply the import-penetration domestic share adjustment",
    )
    marginal_consumption_share: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Share of new labor income that households spend on consumption",
    )
    scenario_name: str = Field(default="unnamed_scenario")

    @model_validator(mode="after")
    def analysis_year_not_before_base_year(self) -> "ScenarioInput":
        if self.analysis_year < self.base_year:
            raise ValueError(
                f"analysis_year ({self.analysis_year}) must be >= base_year ({self.base_year})"
            )
        return self


class EmploymentBreakdown(BaseModel):
    """Aggregated direct, indirect, and induced FTE employment totals.

    Sector-level arrays are stored in ScenarioResult; this model holds the
    economy-wide sums used in dashboard metric cards and comparison tables.
    """

    direct_jobs_fte: float = Field(ge=0)
    indirect_jobs_fte: float = Field(ge=0)
    induced_jobs_fte: float = Field(default=0.0, ge=0)
    total_jobs_fte: float = Field(ge=0)

    @classmethod
    def from_sector_arrays(
        cls,
        direct: list[float],
        indirect: list[float],
        induced: list[float] | None = None,
    ) -> "EmploymentBreakdown":
        """Sum sector-level FTE arrays into an aggregate breakdown.

        Args:
            direct:   FTE by sector from direct project spending.
            indirect: FTE by sector from supply-chain purchases.
            induced:  FTE by sector from household spending (optional).
        """
        d = sum(direct)
        i = sum(indirect)
        n = sum(induced) if induced is not None else 0.0
        return cls(
            direct_jobs_fte=d,
            indirect_jobs_fte=i,
            induced_jobs_fte=n,
            total_jobs_fte=d + i + n,
        )


class ScenarioResult(BaseModel):
    """Complete output from a single scenario run.

    Per-sector arrays (direct_output, indirect_output, etc.) are stored as
    plain lists so the model serialises cleanly without numpy dependencies.
    Array positions correspond to the order of sector_ids.
    """

    scenario_input: ScenarioInput
    sector_ids: list[str]
    sector_names: list[str]

    # Final demand applied to the model (dollars, after inflation and domestic adjustment)
    final_demand: list[float]

    # Output effects (dollars)
    direct_output: list[float]
    indirect_output: list[float]
    induced_output: list[float]

    # Employment effects (FTE)
    direct_employment: list[float]
    indirect_employment: list[float]
    induced_employment: list[float]

    # Ratio used to convert base-year spending to analysis-year dollars
    inflation_adjustment_factor: float = 1.0

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def n_sectors(self) -> int:
        return len(self.sector_ids)

    @property
    def employment(self) -> EmploymentBreakdown:
        """Aggregate employment breakdown across all sectors."""
        return EmploymentBreakdown.from_sector_arrays(
            self.direct_employment,
            self.indirect_employment,
            self.induced_employment if self.scenario_input.include_induced else None,
        )

    @property
    def adjusted_spending(self) -> float:
        """Spending amount inflated from base year to analysis year (dollars)."""
        return self.scenario_input.spending_amount * self.inflation_adjustment_factor

    @property
    def jobs_per_million(self) -> float:
        """Total FTE jobs per million dollars of inflation-adjusted spending."""
        spending_millions = self.adjusted_spending / 1_000_000
        if spending_millions <= 0:
            return 0.0
        return self.employment.total_jobs_fte / spending_millions


class ValidationIssue(BaseModel):
    """A single data or model validation finding."""

    issue_type: str = Field(description="Short category label, e.g. 'duplicate_sector_id'")
    description: str = Field(description="Human-readable explanation of the issue")
    severity: Literal["error", "warning", "info"] = "error"
