# CypressBit Transportation I-O Modeling Lab

> **Internal R&D Prototype — Not a Production System**

This repository demonstrates CypressBit's ability to implement transparent
Input-Output (I-O) economic modeling methods in Python for transportation
infrastructure spending analysis. It is an internally funded R&D prototype,
not a replacement for JOBMOD or any validated government model.

---

## ⚠ Disclaimer

> All sample data in this repository is **synthetic** and is provided for
> demonstration purposes only. Results produced by this prototype are
> **illustrative** and should not be used for policy decisions, procurement
> claims, or any operational purpose without independent review and validation
> using official data sources (BEA I-O tables, BLS employment data, FHWA cost data).

---

## What This Demonstrates

- Python-based I-O model (direct requirements matrix A, Leontief inverse L)
- Employment coefficient calculations (jobs per dollar of sector output)
- Direct, indirect, and induced FTE employment estimation
- Scenario-based analysis with configurable spending, improvement type, and year
- Highway construction cost category mapping with domestic share adjustment
- Interactive Py-Shiny dashboard with downloadable scenario outputs
- Automated test suite and data validation layer
- Reproduction-oriented technical documentation

---

## Quickstart

```bash
# 1. Clone and enter the repository
git clone <repo-url>
cd cypressbit-transport-io-lab

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 3. Install the package with development dependencies
pip install -e ".[dev]"

# 4. Validate sample data
python -m cb_transport_io_lab.cli validate-data

# 5. Run an example scenario
python -m cb_transport_io_lab.cli run-scenario \
  --spending 1000000000 \
  --improvement-type pavement \
  --include-induced \
  --out outputs/example_scenario.csv

# 6. Run the test suite
pytest

# 7. Check code style
ruff check .

# 8. Launch the interactive dashboard
shiny run --reload dashboard/app.py
```

---

## Docker

```bash
docker build -t cypressbit-transport-io-lab .
docker run -p 8000:8000 cypressbit-transport-io-lab
# Open http://localhost:8000
```

---

## Repository Structure

```
cypressbit-transport-io-lab/
├── src/
│   └── cb_transport_io_lab/
│       ├── __init__.py
│       ├── cli.py               # Click CLI commands
│       ├── config.py            # Paths and default parameters
│       ├── data_adapters.py     # Data loading layer
│       ├── schemas.py           # Pydantic v2 data models
│       ├── coefficients.py      # A matrix and employment coefficients
│       ├── leontief.py          # Leontief inverse model
│       ├── employment.py        # Employment estimation
│       ├── scenarios.py         # Scenario runner
│       ├── validation.py        # Data validation checks
│       └── reporting.py         # CSV and Markdown output generation
├── dashboard/
│   ├── app.py                   # Py-Shiny Express dashboard
│   └── assets/
│       └── accessibility.css
├── data/
│   ├── README.md
│   ├── sample/                  # Synthetic demonstration CSVs
│   └── processed/               # Generated artifacts (git-ignored)
├── docs/                        # Technical documentation (12 files)
├── tests/                       # pytest test suite (5 files)
├── outputs/                     # Scenario results (git-ignored)
├── pyproject.toml
├── Makefile
├── Dockerfile
└── .github/workflows/ci.yml
```

---

## Example Scenario

```
Scenario:         $1B pavement improvement demonstration
Spending:         $1,000,000,000
Improvement type: pavement
Base year:        2022 → Analysis year: 2026
Domestic adj.:    enabled
Induced effects:  enabled (marginal consumption share: 0.85)
```

Results are written to `outputs/example_scenario.csv` with one summary row
and one row per sector. Columns include `direct_jobs_fte`, `indirect_jobs_fte`,
`induced_jobs_fte`, `total_jobs_fte`, `jobs_per_million_spending`, and per-sector
output effects.

---

## Documentation

| File | Description |
|------|-------------|
| `docs/methodology.md` | I-O model math, formulas, assumptions |
| `docs/technical_memo.md` | Internal R&D report with worked example |
| `docs/policy_brief.md` | Plain-English summary for non-technical readers |
| `docs/data_dictionary.md` | Schema documentation for all sample CSVs |
| `docs/procurement_evidence.md` | Capability statement and PWS-to-evidence mapping |
| `docs/assumptions_and_limitations.md` | Explicit model limitations |
| `docs/architecture.md` | System architecture and Mermaid data-flow diagram |
| `docs/accessibility_checklist.md` | Section 508 design intentions and gaps |
| `docs/validation_report.md` | Data and test validation status |

---

## Running Tests

```bash
pytest                              # All tests
pytest -v                           # Verbose output
pytest tests/test_leontief.py       # Single file
pytest --cov=cb_transport_io_lab    # With coverage
```

---

## How to Cite

> CypressBit. (2026). *Transportation I-O Modeling Lab: Internal R&D Prototype.*
> CypressBit internal research. Unpublished.

---

## License

MIT License — see [LICENSE](LICENSE).
