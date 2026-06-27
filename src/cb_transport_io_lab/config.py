"""Configuration and path management for cb_transport_io_lab.

All paths are computed relative to the repository root so the package works
regardless of where it is cloned. Environment variables allow the data and
output directories to be overridden at runtime without modifying this file.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Directory layout
# ---------------------------------------------------------------------------

# Package root:  src/cb_transport_io_lab/
PACKAGE_ROOT: Path = Path(__file__).parent

# Repository root:  cypressbit-transport-io-lab/
# (two levels up from the package: src/cb_transport_io_lab → src → repo root)
REPO_ROOT: Path = PACKAGE_ROOT.parent.parent

# Data directories
DATA_DIR: Path = Path(os.environ.get("CB_IO_DATA_DIR", str(REPO_ROOT / "data" / "sample")))
PROCESSED_DIR: Path = REPO_ROOT / "data" / "processed"
OUTPUT_DIR: Path = Path(os.environ.get("CB_IO_OUTPUT_DIR", str(REPO_ROOT / "outputs")))

# ---------------------------------------------------------------------------
# Sample data file paths
# ---------------------------------------------------------------------------

SECTORS_CSV: Path = DATA_DIR / "sectors.csv"
TRANSACTIONS_CSV: Path = DATA_DIR / "transactions.csv"
COST_MIX_CSV: Path = DATA_DIR / "project_cost_mix.csv"
CONSUMER_SPENDING_CSV: Path = DATA_DIR / "consumer_spending_vector.csv"
INFLATION_INDEX_CSV: Path = DATA_DIR / "inflation_index.csv"

# ---------------------------------------------------------------------------
# Default scenario parameters
# ---------------------------------------------------------------------------

DEFAULT_BASE_YEAR: int = 2022
DEFAULT_ANALYSIS_YEAR: int = 2026
DEFAULT_IMPROVEMENT_TYPE: str = "pavement"
DEFAULT_MARGINAL_CONSUMPTION_SHARE: float = 0.85

# ---------------------------------------------------------------------------
# Numerical safeguards
# ---------------------------------------------------------------------------

# Minimum sector output (dollars) used to guard against division by zero when
# computing the A matrix column a_ij = z_ij / x_j.
MIN_OUTPUT_THRESHOLD: float = 1.0

# Maximum allowable condition number for (I - A) before the Leontief solve is
# considered numerically unreliable.
MAX_CONDITION_NUMBER: float = 1e12
