# Data Directory

## Structure

```
data/
├── sample/      — Synthetic demonstration CSVs (committed to git)
└── processed/   — Generated artifacts from processing steps (git-ignored)
```

---

## `data/sample/` — Synthetic Demonstration Data

| File | Purpose |
|------|---------|
| `sectors.csv` | 12 synthetic industry sectors with output, employment, and wage share |
| `transactions.csv` | Inter-sector dollar flows used to build the Z (transaction) matrix |
| `project_cost_mix.csv` | Spending allocation by improvement type (pavement, bridge, safety) |
| `consumer_spending_vector.csv` | Household consumption shares by sector (used for induced effects) |
| `inflation_index.csv` | Synthetic price index 2017–2026 for base-year to analysis-year conversion |

### ⚠ Synthetic Data Disclaimer

**All data in `data/sample/` is SYNTHETIC.**

These files were created to demonstrate the structure and workflow of the
CypressBit Transportation I-O Modeling Lab. They do **not** represent:

- Official BEA Input-Output tables
- BLS employment or compensation statistics
- FHWA highway cost data or BidTabs
- Any other government or proprietary dataset

**Do not use these files for policy decisions, research conclusions, bidding
estimates, or any operational purpose.**

---

## `data/processed/` — Generated Artifacts

This directory holds intermediate outputs from data processing steps (e.g.,
cleaned CSVs, computed matrices). It is **git-ignored** except for the
`.gitkeep` placeholder.

To regenerate processed data, run:

```bash
python -m cb_transport_io_lab.cli validate-data
```

---

## Integrating Real Data

To replace synthetic data with official sources, implement the corresponding
adapter in `src/cb_transport_io_lab/data_adapters.py`:

| Placeholder class | Expected data source |
|-------------------|---------------------|
| `BEADataAdapterPlaceholder` | BEA Use Tables (api.bea.gov) |
| `BLSDataAdapterPlaceholder` | BLS QCEW employment data |
| `BidTabsDataAdapterPlaceholder` | FHWA highway construction cost categories |

Each placeholder raises `NotImplementedError` with the expected schema.
