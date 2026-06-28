"""Data adapters for the CypressBit Transportation I-O Modeling Lab.

Each adapter exposes the same five load methods so callers can swap data
sources without changing model code.  SampleDataAdapter and CSVDataAdapter
are fully implemented.  The three placeholder adapters document the expected
real-data sources and required column schemas.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config


# ---------------------------------------------------------------------------
# Base interface (informal — no ABC overhead needed here)
# ---------------------------------------------------------------------------

class _BaseAdapter:
    """Internal mixin that documents the required interface."""

    def load_sectors(self) -> pd.DataFrame:
        raise NotImplementedError

    def load_transactions(self) -> pd.DataFrame:
        raise NotImplementedError

    def load_cost_mix(self) -> pd.DataFrame:
        raise NotImplementedError

    def load_consumer_spending(self) -> pd.DataFrame:
        raise NotImplementedError

    def load_inflation_index(self) -> pd.DataFrame:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# SampleDataAdapter — reads the bundled sample CSVs via config constants
# ---------------------------------------------------------------------------

class SampleDataAdapter(_BaseAdapter):
    """Load all data from the bundled sample CSV files.

    File paths are taken directly from config constants (SECTORS_CSV, etc.)
    so no arguments are needed.
    """

    def load_sectors(self) -> pd.DataFrame:
        return pd.read_csv(config.SECTORS_CSV)

    def load_transactions(self) -> pd.DataFrame:
        return pd.read_csv(config.TRANSACTIONS_CSV)

    def load_cost_mix(self) -> pd.DataFrame:
        return pd.read_csv(config.COST_MIX_CSV)

    def load_consumer_spending(self) -> pd.DataFrame:
        return pd.read_csv(config.CONSUMER_SPENDING_CSV)

    def load_inflation_index(self) -> pd.DataFrame:
        return pd.read_csv(config.INFLATION_INDEX_CSV)


# ---------------------------------------------------------------------------
# CSVDataAdapter — reads from a user-supplied directory, falls back to config
# ---------------------------------------------------------------------------

class CSVDataAdapter(_BaseAdapter):
    """Load data from CSV files in *base_dir*, falling back to config paths.

    Args:
        base_dir: Directory that contains the CSV files.  If ``None``, each
            file falls back to the corresponding config constant.
    """

    _FILENAMES = {
        "sectors": "sectors.csv",
        "transactions": "transactions.csv",
        "cost_mix": "project_cost_mix.csv",
        "consumer_spending": "consumer_spending_vector.csv",
        "inflation_index": "inflation_index.csv",
    }

    _FALLBACKS = {
        "sectors": config.SECTORS_CSV,
        "transactions": config.TRANSACTIONS_CSV,
        "cost_mix": config.COST_MIX_CSV,
        "consumer_spending": config.CONSUMER_SPENDING_CSV,
        "inflation_index": config.INFLATION_INDEX_CSV,
    }

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base_dir = Path(base_dir) if base_dir is not None else None

    def _resolve(self, key: str) -> Path:
        if self._base_dir is not None:
            return self._base_dir / self._FILENAMES[key]
        return self._FALLBACKS[key]

    def load_sectors(self) -> pd.DataFrame:
        return pd.read_csv(self._resolve("sectors"))

    def load_transactions(self) -> pd.DataFrame:
        return pd.read_csv(self._resolve("transactions"))

    def load_cost_mix(self) -> pd.DataFrame:
        return pd.read_csv(self._resolve("cost_mix"))

    def load_consumer_spending(self) -> pd.DataFrame:
        return pd.read_csv(self._resolve("consumer_spending"))

    def load_inflation_index(self) -> pd.DataFrame:
        return pd.read_csv(self._resolve("inflation_index"))


# ---------------------------------------------------------------------------
# Placeholder adapters — raise NotImplementedError with implementation guides
# ---------------------------------------------------------------------------

class BEADataAdapterPlaceholder(_BaseAdapter):
    """Placeholder for a future BEA I-O data adapter.

    To implement: download the BEA Use tables from api.bea.gov (Dataset:
    "InputOutput", TableID 259 for the domestic Use table), parse the
    supply/use matrix, and reshape into the schemas described below.
    """

    _MSG_SECTORS = (
        "BEADataAdapterPlaceholder.load_sectors() is not implemented.\n"
        "To use BEA I-O data, download the BEA Use tables from api.bea.gov "
        "(Bureau of Economic Analysis Input-Output Accounts, Dataset 'InputOutput'), "
        "implement this adapter, and provide a DataFrame with the expected schema:\n"
        "  sector_id       (str)   — BEA industry code, e.g. '2303'\n"
        "  sector_name     (str)   — industry description\n"
        "  bea_code        (str)   — BEA industry code (same as sector_id for BEA data)\n"
        "  naics_hint      (str)   — corresponding NAICS code or range\n"
        "  output_millions (float) — gross output in millions of dollars (>0)\n"
        "  employment_fte  (float) — full-time equivalent employment (>=0)\n"
        "  wage_share      (float) — labor compensation / gross output, in [0, 1]\n"
        "  notes           (str)   — optional annotation"
    )

    _MSG_TRANSACTIONS = (
        "BEADataAdapterPlaceholder.load_transactions() is not implemented.\n"
        "To use BEA I-O data, download the BEA Use tables from api.bea.gov and "
        "extract the intermediate transaction flows. Provide a DataFrame with:\n"
        "  supplier_sector_id  (str)   — sector_id of the selling industry\n"
        "  purchaser_sector_id (str)   — sector_id of the buying industry\n"
        "  transaction_millions (float) — value of intermediate purchases in millions (>=0)"
    )

    _MSG_COST_MIX = (
        "BEADataAdapterPlaceholder.load_cost_mix() is not implemented.\n"
        "BEA I-O data does not directly supply highway cost mix by improvement type. "
        "Use BidTabsDataAdapterPlaceholder or a custom source. Expected schema:\n"
        "  improvement_type   (str)   — e.g. 'pavement', 'bridge', 'safety'\n"
        "  spending_category  (str)   — cost category label\n"
        "  sector_id          (str)   — receiving sector\n"
        "  share              (float) — fraction of project spending, in [0, 1]; sums to 1 per type\n"
        "  domestic_share     (float) — domestic production fraction, in [0, 1]\n"
        "  notes              (str)   — optional annotation"
    )

    _MSG_CONSUMER = (
        "BEADataAdapterPlaceholder.load_consumer_spending() is not implemented.\n"
        "To use BEA I-O data, derive the personal consumption expenditure (PCE) vector "
        "from the BEA Use table final demand column. Provide a DataFrame with:\n"
        "  sector_id (str)   — sector receiving household spending\n"
        "  share     (float) — fraction of total consumer spending; must sum to 1.0\n"
        "  notes     (str)   — optional annotation"
    )

    _MSG_INFLATION = (
        "BEADataAdapterPlaceholder.load_inflation_index() is not implemented.\n"
        "To use BEA price data, download the BEA price indices for highway construction "
        "from the National Income and Product Accounts. Provide a DataFrame with:\n"
        "  year        (int)   — calendar year\n"
        "  index_value (float) — price index value (base year = 100.0)\n"
        "  notes       (str)   — optional annotation"
    )

    def load_sectors(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_SECTORS)

    def load_transactions(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_TRANSACTIONS)

    def load_cost_mix(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_COST_MIX)

    def load_consumer_spending(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_CONSUMER)

    def load_inflation_index(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_INFLATION)


class BLSDataAdapterPlaceholder(_BaseAdapter):
    """Placeholder for a future BLS QCEW data adapter.

    To implement: download BLS Quarterly Census of Employment and Wages (QCEW)
    data from data.bls.gov/cew/apps/data_views/data_views.htm, aggregate to the
    industry level, and populate the employment and wage columns described below.
    """

    _MSG_SECTORS = (
        "BLSDataAdapterPlaceholder.load_sectors() is not implemented.\n"
        "To use BLS data, download the Quarterly Census of Employment and Wages "
        "(QCEW) from data.bls.gov (Bureau of Labor Statistics), aggregate annual "
        "average employment and wages by NAICS industry, and provide a DataFrame "
        "with the expected schema:\n"
        "  sector_id       (str)   — identifier aligned with your I-O sector list\n"
        "  sector_name     (str)   — industry description\n"
        "  bea_code        (str)   — corresponding BEA industry code\n"
        "  naics_hint      (str)   — NAICS code or range used to filter QCEW records\n"
        "  output_millions (float) — gross output in millions (supplement from BEA; >0)\n"
        "  employment_fte  (float) — annual average FTE from QCEW (>=0)\n"
        "  wage_share      (float) — total wages / gross output, in [0, 1]\n"
        "  notes           (str)   — optional annotation"
    )

    _MSG_TRANSACTIONS = (
        "BLSDataAdapterPlaceholder.load_transactions() is not implemented.\n"
        "BLS QCEW does not provide inter-industry transaction flows. "
        "Use BEADataAdapterPlaceholder for I-O transactions. Expected schema:\n"
        "  supplier_sector_id   (str)   — sector_id of the selling industry\n"
        "  purchaser_sector_id  (str)   — sector_id of the buying industry\n"
        "  transaction_millions (float) — value of intermediate purchases in millions (>=0)"
    )

    _MSG_COST_MIX = (
        "BLSDataAdapterPlaceholder.load_cost_mix() is not implemented.\n"
        "BLS QCEW does not supply highway project cost mix. "
        "Use BidTabsDataAdapterPlaceholder instead. Expected schema:\n"
        "  improvement_type  (str)   — e.g. 'pavement', 'bridge', 'safety'\n"
        "  spending_category (str)   — cost category label\n"
        "  sector_id         (str)   — receiving sector\n"
        "  share             (float) — fraction of project spending, in [0, 1]; sums to 1 per type\n"
        "  domestic_share    (float) — domestic production fraction, in [0, 1]\n"
        "  notes             (str)   — optional annotation"
    )

    _MSG_CONSUMER = (
        "BLSDataAdapterPlaceholder.load_consumer_spending() is not implemented.\n"
        "BLS Consumer Expenditure Survey (CE) can supply household spending shares by "
        "category. Download from bls.gov/cex/, map expenditure categories to sector IDs, "
        "and provide a DataFrame with:\n"
        "  sector_id (str)   — sector receiving household spending\n"
        "  share     (float) — fraction of total consumer spending; must sum to 1.0\n"
        "  notes     (str)   — optional annotation"
    )

    _MSG_INFLATION = (
        "BLSDataAdapterPlaceholder.load_inflation_index() is not implemented.\n"
        "To use BLS price data, download the Producer Price Index (PPI) for highway "
        "and street construction from bls.gov/ppi/. Provide a DataFrame with:\n"
        "  year        (int)   — calendar year\n"
        "  index_value (float) — price index value (base year = 100.0)\n"
        "  notes       (str)   — optional annotation"
    )

    def load_sectors(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_SECTORS)

    def load_transactions(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_TRANSACTIONS)

    def load_cost_mix(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_COST_MIX)

    def load_consumer_spending(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_CONSUMER)

    def load_inflation_index(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_INFLATION)


class BidTabsDataAdapterPlaceholder(_BaseAdapter):
    """Placeholder for a future highway bid-tabs cost-mix adapter.

    To implement: obtain highway construction bid-tabs data (e.g. from FHWA
    or state DOT bid-letting systems), classify bid items into spending
    categories, compute category shares by improvement type, and map each
    category to the appropriate I-O sector.
    """

    _MSG_COST_MIX = (
        "BidTabsDataAdapterPlaceholder.load_cost_mix() is not implemented.\n"
        "To use highway bid-tabs data, obtain contract bid item records from FHWA "
        "or state DOT bid-letting systems (e.g. FHWA's Bid-Tab data available at "
        "www.fhwa.dot.gov/infrastructure/asstmgmt/bidtabs.cfm), classify bid items "
        "into spending categories (e.g. onsite labor, asphalt, steel, engineering), "
        "compute each category's share of total project cost by improvement type, "
        "and map categories to I-O sector IDs. Provide a DataFrame with:\n"
        "  improvement_type  (str)   — project type: 'pavement', 'bridge', 'safety'\n"
        "  spending_category (str)   — bid-tab cost category label\n"
        "  sector_id         (str)   — I-O sector that receives this spending share\n"
        "  share             (float) — fraction of total project spending, in [0, 1]; "
        "must sum to 1.0 across all categories for each improvement_type\n"
        "  domestic_share    (float) — fraction of category spending going to domestic "
        "production (import-penetration adjustment), in [0, 1]\n"
        "  notes             (str)   — optional annotation or data source reference"
    )

    _MSG_NOT_APPLICABLE = (
        "BidTabsDataAdapterPlaceholder.{method}() is not applicable.\n"
        "Bid-tabs data covers project cost mix only. "
        "Use BEADataAdapterPlaceholder for I-O sector and transaction data."
    )

    def load_sectors(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_NOT_APPLICABLE.format(method="load_sectors"))

    def load_transactions(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_NOT_APPLICABLE.format(method="load_transactions"))

    def load_cost_mix(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_COST_MIX)

    def load_consumer_spending(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_NOT_APPLICABLE.format(method="load_consumer_spending"))

    def load_inflation_index(self) -> pd.DataFrame:
        raise NotImplementedError(self._MSG_NOT_APPLICABLE.format(method="load_inflation_index"))
