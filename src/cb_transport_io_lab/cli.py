"""Command-line interface for the CypressBit Transportation I-O Modeling Lab.

Entry point: cb-io-lab  (configured in pyproject.toml [project.scripts])
Module execution: python -m cb_transport_io_lab.cli <command> ...

Commands:
    validate-data       Validate all sample data files and report issues.
    run-scenario        Run a single I-O scenario and write a CSV result.
    compare-scenarios   Run pavement/bridge/safety variants and compare them.
    write-docs          Write the methodology summary and validation report.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    _console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _print(msg: str, style: str = "") -> None:
    if HAS_RICH:
        _console.print(msg, style=style or None)
    else:
        click.echo(msg)


def _print_error(msg: str) -> None:
    if HAS_RICH:
        _console.print(f"[bold red]ERROR:[/bold red] {msg}")
    else:
        click.echo(f"ERROR: {msg}", err=True)


def _print_success(msg: str) -> None:
    if HAS_RICH:
        _console.print(f"[bold green]✓[/bold green] {msg}")
    else:
        click.echo(f"OK: {msg}")


def _print_warning(msg: str) -> None:
    if HAS_RICH:
        _console.print(f"[yellow]⚠[/yellow] {msg}")
    else:
        click.echo(f"WARNING: {msg}")


def _print_scenario_summary(result) -> None:
    """Print a formatted summary of a ScenarioResult."""
    si = result.scenario_input
    emp = result.employment

    if HAS_RICH:
        table = Table(title=f"Scenario: {si.scenario_name}", show_header=True)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Spending (nominal)", f"${si.spending_amount:>20,.0f}")
        table.add_row(
            f"Adjusted spending ({si.base_year}→{si.analysis_year})",
            f"${result.adjusted_spending:>20,.0f}",
        )
        table.add_row("Inflation factor", f"{result.inflation_adjustment_factor:.6f}")
        table.add_row("Improvement type", si.improvement_type)
        table.add_row("", "")
        table.add_row("[cyan]Direct FTE[/cyan]", f"{emp.direct_jobs_fte:>20,.1f}")
        table.add_row("[cyan]Indirect FTE[/cyan]", f"{emp.indirect_jobs_fte:>20,.1f}")
        if si.include_induced:
            table.add_row(
                "[cyan]Induced FTE[/cyan] [dim](prototype)[/dim]",
                f"{emp.induced_jobs_fte:>20,.1f}",
            )
        table.add_row("[bold]Total FTE[/bold]", f"[bold]{emp.total_jobs_fte:>20,.1f}[/bold]")
        table.add_row("Jobs per $M spending", f"{result.jobs_per_million:>20.4f}")
        _console.print(table)
    else:
        click.echo(f"\nScenario: {si.scenario_name}")
        click.echo(f"  Spending (nominal):              ${si.spending_amount:>15,.0f}")
        click.echo(f"  Adjusted ({si.base_year}→{si.analysis_year}):         ${result.adjusted_spending:>15,.0f}")
        click.echo(f"  Inflation factor:                 {result.inflation_adjustment_factor:.6f}")
        click.echo(f"  Improvement type:                 {si.improvement_type}")
        click.echo(f"  Direct FTE:                     {emp.direct_jobs_fte:>15,.1f}")
        click.echo(f"  Indirect FTE:                   {emp.indirect_jobs_fte:>15,.1f}")
        if si.include_induced:
            click.echo(f"  Induced FTE (prototype):        {emp.induced_jobs_fte:>15,.1f}")
        click.echo(f"  Total FTE:                      {emp.total_jobs_fte:>15,.1f}")
        click.echo(f"  Jobs per $M spending:           {result.jobs_per_million:>15.4f}")


# ---------------------------------------------------------------------------
# Click group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="cb-transport-io-lab")
def main() -> None:
    """CypressBit Transportation I-O Modeling Lab CLI.

    Run 'cb-io-lab COMMAND --help' for details on each command.
    """


# ---------------------------------------------------------------------------
# validate-data
# ---------------------------------------------------------------------------

@main.command("validate-data")
def validate_data() -> None:
    """Validate all sample data files and report any issues."""
    from .data_adapters import SampleDataAdapter
    from .validation import run_all_validations, has_errors

    _print("[bold]Running data validation…[/bold]" if HAS_RICH else "Running data validation...")

    adapter = SampleDataAdapter()
    sectors_df = adapter.load_sectors()
    transactions_df = adapter.load_transactions()
    cost_mix_df = adapter.load_cost_mix()
    consumer_df = adapter.load_consumer_spending()

    issues = run_all_validations(sectors_df, transactions_df, cost_mix_df, consumer_df)

    if not issues:
        _print_success("All validation checks passed. No issues found.")
        return

    _print(f"\nFound {len(issues)} issue(s):\n")
    for iss in issues:
        if iss.severity == "error":
            _print_error(f"[{iss.issue_type}] {iss.description}")
        elif iss.severity == "warning":
            _print_warning(f"[{iss.issue_type}] {iss.description}")
        else:
            _print(f"INFO [{iss.issue_type}] {iss.description}")

    if has_errors(issues):
        _print_error("Validation failed with errors.")
        sys.exit(1)
    else:
        _print_warning("Validation completed with warnings only.")


# ---------------------------------------------------------------------------
# run-scenario
# ---------------------------------------------------------------------------

@main.command("run-scenario")
@click.option("--spending", required=True, type=float,
              help="Total project spending in dollars.")
@click.option("--improvement-type", default="pavement", show_default=True,
              type=click.Choice(["pavement", "bridge", "safety"]),
              help="Project improvement type.")
@click.option("--base-year", default=2022, show_default=True, type=int,
              help="Dollar basis year for the spending amount.")
@click.option("--analysis-year", default=2026, show_default=True, type=int,
              help="Target analysis year (for inflation adjustment).")
@click.option("--include-induced/--no-induced", default=True, show_default=True,
              help="Include simplified induced employment effects.")
@click.option("--domestic-adjustment/--no-domestic-adjustment", default=True,
              show_default=True,
              help="Apply import-penetration domestic share adjustment.")
@click.option("--marginal-consumption-share", default=0.85, show_default=True,
              type=float, help="Share of new labor income spent on consumption (0–1).")
@click.option("--scenario-name", default=None, type=str,
              help="Optional display name for the scenario.")
@click.option("--out", required=True, type=click.Path(),
              help="Output CSV file path.")
def run_scenario_cmd(
    spending: float,
    improvement_type: str,
    base_year: int,
    analysis_year: int,
    include_induced: bool,
    domestic_adjustment: bool,
    marginal_consumption_share: float,
    scenario_name: str | None,
    out: str,
) -> None:
    """Run a single I-O scenario and write the results to a CSV file."""
    from .scenarios import run_scenario
    from .schemas import ScenarioInput
    from .reporting import write_scenario_csv

    if scenario_name is None:
        scenario_name = f"{improvement_type}_{spending/1e6:.0f}M"

    si = ScenarioInput(
        spending_amount=spending,
        base_year=base_year,
        analysis_year=analysis_year,
        improvement_type=improvement_type,
        include_induced=include_induced,
        domestic_adjustment=domestic_adjustment,
        marginal_consumption_share=marginal_consumption_share,
        scenario_name=scenario_name,
    )

    _print("[bold]Running scenario…[/bold]" if HAS_RICH else "Running scenario...")
    try:
        result = run_scenario(si)
    except Exception as exc:
        _print_error(f"Scenario run failed: {exc}")
        sys.exit(1)

    _print_scenario_summary(result)

    try:
        write_scenario_csv(result, out)
        _print_success(f"Results written to: {out}")
    except Exception as exc:
        _print_error(f"Failed to write CSV: {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# compare-scenarios
# ---------------------------------------------------------------------------

@main.command("compare-scenarios")
@click.option("--spending", required=True, type=float,
              help="Total project spending in dollars (applied to all variants).")
@click.option("--out", required=True, type=click.Path(),
              help="Output CSV file path for the comparison table.")
@click.option("--base-year", default=2022, show_default=True, type=int,
              help="Dollar basis year for the spending amount.")
@click.option("--analysis-year", default=2026, show_default=True, type=int,
              help="Target analysis year (for inflation adjustment).")
def compare_scenarios_cmd(
    spending: float,
    out: str,
    base_year: int,
    analysis_year: int,
) -> None:
    """Run pavement, bridge, and safety scenarios and write a comparison CSV."""
    from .scenarios import compare_scenarios
    from .schemas import ScenarioInput

    scenarios = [
        ScenarioInput(
            spending_amount=spending,
            base_year=base_year,
            analysis_year=analysis_year,
            improvement_type=itype,
            include_induced=True,
            domestic_adjustment=True,
            marginal_consumption_share=0.85,
            scenario_name=f"{itype}_{spending/1e6:.0f}M",
        )
        for itype in ("pavement", "bridge", "safety")
    ]

    _print("[bold]Running 3 scenario variants…[/bold]" if HAS_RICH else "Running 3 scenario variants...")
    try:
        df = compare_scenarios(scenarios)
    except Exception as exc:
        _print_error(f"Scenario comparison failed: {exc}")
        sys.exit(1)

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    _print_success(f"Comparison written to: {out}")

    if HAS_RICH:
        table = Table(title="Scenario Comparison", show_header=True)
        for col in ["scenario_name", "total_jobs_fte", "direct_jobs_fte",
                    "indirect_jobs_fte", "induced_jobs_fte", "jobs_per_million"]:
            table.add_column(col, justify="right" if col != "scenario_name" else "left")
        for _, row in df.iterrows():
            table.add_row(
                str(row["scenario_name"]),
                f"{row['total_jobs_fte']:,.1f}",
                f"{row['direct_jobs_fte']:,.1f}",
                f"{row['indirect_jobs_fte']:,.1f}",
                f"{row['induced_jobs_fte']:,.1f}",
                f"{row['jobs_per_million']:.4f}",
            )
        _console.print(table)
    else:
        click.echo("\n" + df[["scenario_name", "total_jobs_fte", "jobs_per_million"]].to_string(index=False))


# ---------------------------------------------------------------------------
# write-docs
# ---------------------------------------------------------------------------

@main.command("write-docs")
@click.option("--out-dir", default="docs", show_default=True, type=click.Path(),
              help="Directory to write documentation files into.")
def write_docs(out_dir: str) -> None:
    """Write methodology summary and validation report to the docs directory."""
    from .data_adapters import SampleDataAdapter
    from .validation import run_all_validations
    from .reporting import write_methodology_summary, write_validation_report

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    methodology_path = out / "methodology_summary.md"
    write_methodology_summary(methodology_path)
    _print_success(f"Methodology summary written to: {methodology_path}")

    adapter = SampleDataAdapter()
    sectors_df = adapter.load_sectors()
    transactions_df = adapter.load_transactions()
    cost_mix_df = adapter.load_cost_mix()
    consumer_df = adapter.load_consumer_spending()

    issues = run_all_validations(sectors_df, transactions_df, cost_mix_df, consumer_df)
    validation_path = out / "validation_report.md"
    write_validation_report(issues, validation_path)
    _print_success(f"Validation report written to: {validation_path}")

    if issues:
        _print_warning(f"{len(issues)} validation issue(s) recorded in the report.")
    else:
        _print_success("No validation issues found.")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
