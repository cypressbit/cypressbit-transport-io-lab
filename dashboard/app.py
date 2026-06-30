"""CypressBit Transportation I-O Modeling Lab — Py-Shiny Dashboard.

Sections 9.1–9.3 of the build instructions.

Run from the repo root:
    shiny run dashboard/app.py --reload

Or:
    cd dashboard && shiny run app.py --reload
"""

# sys.path must be patched first so the src package is importable
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ── stdlib ────────────────────────────────────────────────────────────────────
import io

# ── matplotlib: set non-interactive backend before pyplot import ──────────────
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ── data / reactive ───────────────────────────────────────────────────────────
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui

# ── local package ─────────────────────────────────────────────────────────────
from cb_transport_io_lab.schemas import ScenarioInput
from cb_transport_io_lab.scenarios import run_scenario
from cb_transport_io_lab.reporting import result_to_dataframe

# ── Constants ─────────────────────────────────────────────────────────────────
_YEARS = {str(y): str(y) for y in range(2017, 2027)}
_IMP_TYPES = {"pavement": "Pavement", "bridge": "Bridge", "safety": "Safety"}
_CSS_PATH = Path(__file__).parent / "assets" / "accessibility.css"

# ── Reactive state (hold result + any error message) ──────────────────────────
_result: reactive.Value = reactive.Value(None)
_error: reactive.Value = reactive.Value("")

# ── Chart helpers ──────────────────────────────────────────────────────────────

def _placeholder_fig(msg: str = "Click 'Run Scenario' to view results"):
    fig, ax = plt.subplots(figsize=(5, 3.2))
    ax.text(
        0.5, 0.5, msg,
        ha="center", va="center",
        transform=ax.transAxes,
        fontsize=10, color="#555555",
    )
    ax.axis("off")
    fig.patch.set_facecolor("#f8fafc")
    plt.tight_layout()
    return fig


def _style_ax(ax):
    """Apply consistent, accessible spine/grid styling to a matplotlib axes."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#8fa4b8")
    ax.spines["bottom"].set_color("#8fa4b8")
    ax.tick_params(colors="#1a1a1a", labelsize=8)
    ax.yaxis.label.set_color("#1a1a1a")
    ax.xaxis.label.set_color("#1a1a1a")


# =============================================================================
# PAGE CONFIG
# =============================================================================

ui.page_opts(
    title="CypressBit Transportation I-O Modeling Lab",
    fillable=False,
    lang="en",
)

# Inline the CSS so it works regardless of working directory
ui.include_css(_CSS_PATH, method="inline")

# =============================================================================
# APPLICATION HEADER
# =============================================================================

with ui.div(class_="cb-header"):
    ui.h1(
        "CypressBit Transportation I-O Modeling Lab",
        id="app-title",
    )
    ui.p(
        "A transparent Python prototype for scenario-based transportation "
        "infrastructure employment estimation.",
        class_="cb-subtitle",
    )

# Synthetic-data disclaimer — always visible
with ui.div(style="padding: 0.4rem 1rem 0;"):
    ui.div(
        ui.tags.strong("⚠ Synthetic Data — Not for Official Use.  "),
        "This prototype uses synthetic sample data for demonstration purposes only. "
        "Results do not represent official government estimates and have not been "
        "validated by FHWA, BEA, BLS, or any other agency. "
        "This is not an implementation of JOBMOD or any official highway employment model.",
        class_="cb-disclaimer",
        role="note",
        **{"aria-label": "Synthetic data notice"},
    )

# =============================================================================
# SIDEBAR + MAIN LAYOUT
# =============================================================================

with ui.layout_sidebar():

    # ── SIDEBAR ────────────────────────────────────────────────────────────────
    with ui.sidebar(title="Scenario Parameters", width=320):

        ui.input_numeric(
            "spending",
            "Project Spending ($)",
            value=1_000_000_000,
            min=1_000_000,
            step=10_000_000,
        )

        ui.input_select(
            "improvement_type",
            "Improvement Type",
            choices=_IMP_TYPES,
            selected="pavement",
        )

        ui.input_select(
            "base_year",
            "Base Year",
            choices=_YEARS,
            selected="2022",
        )

        ui.input_select(
            "analysis_year",
            "Analysis Year",
            choices=_YEARS,
            selected="2026",
        )

        ui.input_checkbox(
            "include_induced",
            "Include Induced Effects",
            value=True,
        )

        ui.input_checkbox(
            "domestic_adjustment",
            "Apply Domestic Share Adjustment",
            value=True,
        )

        ui.input_slider(
            "mcs",
            "Marginal Consumption Share",
            min=0.50,
            max=1.00,
            value=0.85,
            step=0.05,
        )

        ui.hr()

        ui.input_action_button(
            "run_btn",
            "▶ Run Scenario",
            class_="btn-primary w-100",
        )

        ui.br()

        @render.download(
            filename="scenario_results.csv",
            media_type="text/csv",
            label="⬇ Download Results CSV",
        )
        def download_results():
            r = _result.get()
            if r is None:
                yield "No results available. Please run a scenario first.\n"
                return
            buf = io.StringIO()
            result_to_dataframe(r).to_csv(buf, index=False)
            yield buf.getvalue()

    # ── MAIN PANEL ─────────────────────────────────────────────────────────────

    # Error display (hidden when no error)
    @render.ui
    def error_display():
        err = _error.get()
        if not err:
            return ui.div()
        return ui.div(
            ui.tags.strong("⚠ Error: "),
            err,
            class_="cb-error-box",
            role="alert",
        )

    # -- Metric cards ----------------------------------------------------------
    ui.h2("Key Results", id="results-heading", style="margin-top:0.5rem;")

    @render.ui
    def metric_cards():
        r = _result.get()
        emp = r.employment if r else None
        include_induced = r.scenario_input.include_induced if r else input.include_induced()

        def _card(label: str, value: str, note: str = "") -> ui.Tag:
            return ui.div(
                ui.p(label, class_="cb-metric-label"),
                ui.p(value, class_="cb-metric-value"),
                ui.p(note, class_="cb-metric-note"),
                class_="cb-metric-card",
                role="region",
                **{"aria-label": label},
            )

        total_note = "Direct + Indirect"
        if include_induced:
            total_note += " + Induced"

        cards = [
            _card("Total FTE Jobs",
                  f"{emp.total_jobs_fte:,.1f}" if emp else "—",
                  total_note),
            _card("Direct FTE",
                  f"{emp.direct_jobs_fte:,.1f}" if emp else "—",
                  "Project-facing sectors"),
            _card("Indirect FTE",
                  f"{emp.indirect_jobs_fte:,.1f}" if emp else "—",
                  "Supply-chain effects"),
        ]

        if include_induced:
            cards.append(
                _card("Induced FTE",
                      f"{emp.induced_jobs_fte:,.1f}" if emp else "—",
                      "Simplified prototype ⚠")
            )

        cards.append(
            _card("Jobs per $1M Spent",
                  f"{r.jobs_per_million:.2f}" if r else "—",
                  "Inflation-adjusted spending")
        )

        return ui.div(*cards, class_="cb-metric-grid", role="list",
                      **{"aria-label": "Scenario result metrics"})

    # -- Side-by-side charts ---------------------------------------------------
    ui.h2("Employment Charts", style="margin-top:0.5rem;")

    with ui.layout_columns(col_widths=[6, 6]):

        # Chart 1: Direct / Indirect / Induced breakdown
        with ui.card():
            ui.card_header("Employment Effects by Type")

            @render.plot(
                alt=(
                    "Vertical bar chart showing direct, indirect, and "
                    "(if enabled) induced FTE employment. "
                    "See text summary below for values."
                )
            )
            def effect_chart():
                r = _result.get()
                if r is None:
                    return _placeholder_fig()

                emp = r.employment
                include = r.scenario_input.include_induced

                labels = ["Direct", "Indirect"]
                values = [emp.direct_jobs_fte, emp.indirect_jobs_fte]
                # Use distinct hatches so color is not the sole differentiator
                colors = ["#0b3d6b", "#2471a3"]
                hatches = ["///", "\\\\\\"]

                if include:
                    labels.append("Induced*")
                    values.append(emp.induced_jobs_fte)
                    colors.append("#5dade2")
                    hatches.append("...")

                fig, ax = plt.subplots(figsize=(5, 3.5))
                bars = ax.bar(labels, values, color=colors, width=0.55, zorder=2)
                for bar, hatch in zip(bars, hatches):
                    bar.set_hatch(hatch)
                    bar.set_edgecolor("#ffffff")
                    bar.set_linewidth(0.8)

                # Value labels above each bar
                for bar, val in zip(bars, values):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + max(values) * 0.02,
                        f"{val:,.0f}",
                        ha="center", va="bottom",
                        fontsize=8.5, fontweight="bold", color="#1a1a1a",
                    )

                ax.set_ylabel("FTE Jobs", fontsize=9)
                ax.set_title(
                    r.scenario_input.improvement_type.title() + " Improvement Scenario",
                    fontsize=9.5, fontweight="bold", color="#0b3d6b",
                )
                ax.yaxis.set_major_formatter(mticker.FuncFormatter(
                    lambda x, _: f"{x:,.0f}"
                ))
                ax.set_ylim(0, max(values) * 1.18)
                ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
                _style_ax(ax)
                plt.tight_layout()
                return fig

            # Text summary (WCAG: charts must have text summaries)
            @render.ui
            def effect_chart_caption():
                r = _result.get()
                if r is None:
                    return ui.div()
                emp = r.employment
                parts = [
                    f"{emp.direct_jobs_fte:,.0f} direct",
                    f"{emp.indirect_jobs_fte:,.0f} indirect",
                ]
                if r.scenario_input.include_induced:
                    parts.append(f"{emp.induced_jobs_fte:,.0f} induced (prototype)")
                return ui.p(
                    f"Total: {emp.total_jobs_fte:,.0f} FTE — "
                    + ", ".join(parts) + ".",
                    class_="cb-chart-caption",
                )

        # Chart 2: Top sectors by employment
        with ui.card():
            ui.card_header("Top Sectors by Employment Impact")

            @render.plot(
                alt=(
                    "Horizontal bar chart showing top sectors by combined FTE employment. "
                    "See text summary below for leading sector."
                )
            )
            def sector_chart():
                r = _result.get()
                if r is None:
                    return _placeholder_fig()

                df = result_to_dataframe(r)
                top = (
                    df[df["sector_id"] != "TOTAL"]
                    .nlargest(8, "employment_fte")
                    .reset_index(drop=True)
                )

                # Truncate long sector names for readability
                names = [
                    (n[:30] + "…") if len(n) > 30 else n
                    for n in top["sector_name"]
                ]
                vals = top["employment_fte"].values

                # Gradient shading (dark = high), hatches vary for accessibility
                norm_vals = vals / max(vals) if max(vals) > 0 else vals
                colors = [plt.cm.Blues(0.35 + 0.55 * v) for v in norm_vals]
                hatches = (["///", "\\\\\\", "...", "|||", "---",
                            "xxx", "+++", "ooo"] * 2)[:len(vals)]

                fig, ax = plt.subplots(figsize=(5, 3.5))
                y_pos = range(len(names))

                # Reverse so highest value appears at top
                bars = ax.barh(
                    list(reversed(names)),
                    list(reversed(vals)),
                    color=list(reversed(colors)),
                    edgecolor="#cccccc",
                    linewidth=0.5,
                    zorder=2,
                )
                for bar, hatch in zip(bars, reversed(hatches)):
                    bar.set_hatch(hatch)
                    bar.set_edgecolor("#aaaaaa")

                # Value labels
                for bar, val in zip(bars, reversed(vals)):
                    ax.text(
                        val + max(vals) * 0.015,
                        bar.get_y() + bar.get_height() / 2,
                        f"{val:,.0f}",
                        va="center", fontsize=7.5, color="#1a1a1a",
                    )

                ax.set_xlabel("FTE Jobs", fontsize=9)
                ax.xaxis.set_major_formatter(mticker.FuncFormatter(
                    lambda x, _: f"{x:,.0f}"
                ))
                ax.grid(axis="x", linestyle="--", alpha=0.4, zorder=0)
                _style_ax(ax)
                ax.tick_params(axis="y", labelsize=7.5)
                plt.tight_layout()
                return fig

            @render.ui
            def sector_chart_caption():
                r = _result.get()
                if r is None:
                    return ui.div()
                df = result_to_dataframe(r)
                top1 = (
                    df[df["sector_id"] != "TOTAL"]
                    .nlargest(1, "employment_fte")
                )
                if top1.empty:
                    return ui.div()
                name = top1.iloc[0]["sector_name"]
                val = top1.iloc[0]["employment_fte"]
                return ui.p(
                    f"Top 8 sectors by combined employment impact (direct + indirect + induced). "
                    f"Highest: {name} ({val:,.0f} FTE).",
                    class_="cb-chart-caption",
                )

    # -- Output impact table ---------------------------------------------------
    ui.h2("Data Tables", style="margin-top:0.75rem;")

    with ui.card():
        ui.card_header("Output Impact by Sector (millions of dollars)")

        @render.data_frame
        def output_table():
            r = _result.get()
            if r is None:
                return render.DataGrid(
                    pd.DataFrame({"Status": ["Click 'Run Scenario' to view results."]})
                )
            df = result_to_dataframe(r)
            disp = df[
                ["sector_id", "sector_name", "direct_output",
                 "indirect_output", "induced_output", "output_effect"]
            ].copy()
            for col in ["direct_output", "indirect_output", "induced_output", "output_effect"]:
                disp[col] = (disp[col] / 1_000_000).round(2)
            disp.columns = [
                "Sector ID", "Sector Name",
                "Direct ($M)", "Indirect ($M)", "Induced ($M)",
                "Total Output Effect ($M)",
            ]
            return render.DataGrid(disp, summary=False, height="380px")

    # -- Employment impact table -----------------------------------------------
    with ui.card():
        ui.card_header("Employment Impact by Sector (FTE jobs)")

        @render.data_frame
        def employment_table():
            r = _result.get()
            if r is None:
                return render.DataGrid(
                    pd.DataFrame({"Status": ["Click 'Run Scenario' to view results."]})
                )
            emp = r.employment
            sector_totals = [
                round(d + i + n, 1)
                for d, i, n in zip(
                    r.direct_employment,
                    r.indirect_employment,
                    r.induced_employment,
                )
            ]
            df = result_to_dataframe(r)
            disp = pd.DataFrame(
                {
                    "Sector ID": df["sector_id"].tolist(),
                    "Sector Name": df["sector_name"].tolist(),
                    "Direct FTE": [round(emp.direct_jobs_fte, 1)]
                    + [round(v, 1) for v in r.direct_employment],
                    "Indirect FTE": [round(emp.indirect_jobs_fte, 1)]
                    + [round(v, 1) for v in r.indirect_employment],
                    "Induced FTE": [round(emp.induced_jobs_fte, 1)]
                    + [round(v, 1) for v in r.induced_employment],
                    "Total FTE": [round(emp.total_jobs_fte, 1)] + sector_totals,
                }
            )
            return render.DataGrid(disp, summary=False, height="380px")

    # -- Methodology notes + Data assumptions accordion ─────────────────────────
    ui.h2("Reference Information", style="margin-top:0.75rem;")

    with ui.accordion(id="info_accordion", open=False):

        with ui.accordion_panel("Methodology Notes"):
            ui.h3("Input-Output Model Overview")
            ui.p(
                "This prototype implements a static, open Leontief Input-Output model "
                "applied to highway transportation spending. "
                "It estimates FTE employment effects across three categories: direct, "
                "indirect (supply-chain), and optionally induced (household spending)."
            )

            ui.h4("Direct Requirements Matrix (A)")
            ui.tags.pre("a[i,j] = z[i,j] / x[j]")
            ui.p(
                "Where z[i,j] is the dollar flow from supplier sector i to purchaser "
                "sector j (from the Use table), and x[j] is sector j's gross output. "
                "Computed by column-wise division: A = Z / x."
            )

            ui.h4("Leontief Inverse (L)")
            ui.tags.pre("L = (I − A)⁻¹\ntotal_output = L @ f")
            ui.p(
                "L captures all direct and indirect upstream requirements. "
                "Scenario output is computed using numpy.linalg.solve for numerical "
                "stability; the explicit inverse is also available for multiplier reporting."
            )

            ui.h4("Employment Coefficients")
            ui.tags.pre("e[i] = employment_fte[i] / (output_millions[i] × 1,000,000)\njobs[i] = e[i] × output[i]")

            ui.h4("Output Effects")
            ui.tags.pre(
                "direct_output[i]   = f[i]                         (final demand)\n"
                "indirect_output[i] = total_output[i] − f[i]       (supply-chain)\n"
                "total_output       = solve(I − A, f)"
            )

            ui.h4("Induced Effects — Simplified Prototype")
            ui.div(
                ui.tags.strong("⚠ This is a simplified demonstration, not a validated Type II multiplier model."),
                ui.tags.pre(
                    "labor_income = Σ ( total_output[i] × wage_share[i] )\n"
                    "household_f  = labor_income × marginal_consumption_share\n"
                    "              × consumer_spending_shares\n"
                    "induced_output = solve(I − A, household_f)"
                ),
                ui.p(
                    "The marginal consumption share (default 0.85) controls what fraction "
                    "of new labor income is re-spent on consumption. "
                    "This method would require subject-matter review before operational use."
                ),
                class_="cb-disclaimer",
            )

            ui.h4("Inflation Adjustment")
            ui.tags.pre(
                "inflation_factor     = index[analysis_year] / index[base_year]\n"
                "adjusted_spending    = spending × inflation_factor"
            )
            ui.p(
                "The inflation index uses a synthetic price series. "
                "Real use requires BLS PPI or BEA price deflators."
            )

        with ui.accordion_panel("Data Assumptions"):
            ui.p(
                "The following assumptions apply to all results produced by this prototype.",
                style="font-weight:600;",
            )
            ui.tags.ul(
                ui.tags.li(
                    "All sector output, employment, wage share, and transaction data are "
                    "synthetic and illustrative. Do not cite results from this prototype."
                ),
                ui.tags.li(
                    "Project cost mix proportions (pavement, bridge, safety) are illustrative "
                    "estimates, not derived from official FHWA bid-tab data."
                ),
                ui.tags.li(
                    "The inflation index is a synthetic series. Real use requires BLS PPI "
                    "for highway construction or BEA price deflators."
                ),
                ui.tags.li(
                    "Consumer spending shares are illustrative. Real use requires BLS "
                    "Consumer Expenditure Survey data mapped to I-O sectors."
                ),
                ui.tags.li(
                    "The domestic share adjustment is a prototype import-penetration model "
                    "and has not been calibrated against official trade statistics."
                ),
                ui.tags.li(
                    "This software has not been validated by FHWA, BEA, BLS, or any "
                    "other federal agency. It is intended for internal R&D demonstration only."
                ),
                ui.tags.li(
                    "One job = one full-time equivalent (FTE) of 2,080 hours, unless "
                    "the data source defines otherwise."
                ),
            )


# =============================================================================
# REACTIVE LOGIC — outside all UI context managers
# =============================================================================

@reactive.effect
@reactive.event(input.run_btn)
def _do_run() -> None:
    """Run the I-O scenario when the button is clicked.

    Reads all sidebar inputs, builds a ScenarioInput, calls run_scenario,
    and stores the result in the shared reactive Value.  Any exception is
    captured as a user-visible error message.
    """
    _error.set("")

    raw_spending = input.spending()
    if raw_spending is None or raw_spending <= 0:
        _error.set("Project spending must be a positive number.")
        _result.set(None)
        return

    base_yr = int(input.base_year())
    analysis_yr = int(input.analysis_year())
    if analysis_yr < base_yr:
        _error.set(
            f"Analysis Year ({analysis_yr}) cannot be earlier than "
            f"Base Year ({base_yr})."
        )
        _result.set(None)
        return

    try:
        si = ScenarioInput(
            spending_amount=float(raw_spending),
            base_year=base_yr,
            analysis_year=analysis_yr,
            improvement_type=input.improvement_type(),
            include_induced=bool(input.include_induced()),
            domestic_adjustment=bool(input.domestic_adjustment()),
            marginal_consumption_share=float(input.mcs()),
            scenario_name=(
                f"{input.improvement_type()}_{float(raw_spending)/1e6:.0f}M"
            ),
        )
        _result.set(run_scenario(si))
    except Exception as exc:
        _error.set(str(exc))
        _result.set(None)
