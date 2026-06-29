"""I-O coefficient calculations for the CypressBit Transportation I-O Modeling Lab.

Implements the direct requirements matrix (A), employment coefficients, and
jobs-per-million ratios that feed into LeontiefModel and the scenario engine.

Mathematical reference (Section 6.2 of the build instructions):
    a_ij = z_ij / x_j          (technical coefficient: input from i per unit of j's output)
    A    = Z / x               (column-wise division; x_j is purchaser j's gross output)
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from . import config


def build_transaction_matrix(
    transactions_df: pd.DataFrame, sectors_df: pd.DataFrame
) -> np.ndarray:
    """Build the n×n intermediate transaction matrix Z (dollars).

    Args:
        transactions_df: DataFrame with columns supplier_sector_id,
            purchaser_sector_id, transaction_millions.
        sectors_df: DataFrame with column sector_id that defines the sector
            ordering and size of the matrix.

    Returns:
        Z (n, n) float64 array.  Z[i, j] is the dollar flow from supplier
        sector i to purchaser sector j.  Row and column ordering follows
        sectors_df['sector_id'].  Sector pairs not listed in transactions_df
        are set to zero.
    """
    sector_ids = sectors_df["sector_id"].tolist()
    idx = {sid: i for i, sid in enumerate(sector_ids)}
    n = len(sector_ids)
    Z = np.zeros((n, n), dtype=np.float64)

    for _, row in transactions_df.iterrows():
        supplier = row["supplier_sector_id"]
        purchaser = row["purchaser_sector_id"]
        if supplier in idx and purchaser in idx:
            Z[idx[supplier], idx[purchaser]] = float(row["transaction_millions"]) * 1_000_000.0

    return Z


def build_output_vector(sectors_df: pd.DataFrame) -> np.ndarray:
    """Build the gross-output vector x (dollars).

    Args:
        sectors_df: DataFrame with columns sector_id and output_millions.
            Row ordering determines the position in the returned vector.

    Returns:
        x (n,) float64 array in dollars.
    """
    return sectors_df["output_millions"].to_numpy(dtype=np.float64) * 1_000_000.0


def calculate_direct_requirements(Z: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Calculate the direct requirements (technical coefficient) matrix A.

    Each element a_ij = z_ij / x_j: the fraction of purchaser j's gross output
    that is sourced as intermediate input from supplier i.

    Args:
        Z: (n, n) transaction matrix in dollars (from build_transaction_matrix).
        x: (n,) output vector in dollars (from build_output_vector).

    Returns:
        A (n, n) float64 array of technical coefficients.

    Raises:
        ValueError: If dimensions are inconsistent or any x_j is below
            config.MIN_OUTPUT_THRESHOLD (guards against division by zero).

    Warns:
        UserWarning: If any a_ij > 1, which may indicate data quality issues.
    """
    if Z.ndim != 2 or Z.shape[0] != Z.shape[1]:
        raise ValueError(
            f"Z must be a square 2-D array; got shape {Z.shape}"
        )
    n = Z.shape[0]
    if x.ndim != 1 or x.shape[0] != n:
        raise ValueError(
            f"x must be a 1-D array of length {n} to match Z; got shape {x.shape}"
        )

    below_threshold = np.where(x < config.MIN_OUTPUT_THRESHOLD)[0]
    if below_threshold.size > 0:
        raise ValueError(
            f"Output vector x has {below_threshold.size} value(s) below "
            f"MIN_OUTPUT_THRESHOLD ({config.MIN_OUTPUT_THRESHOLD}). "
            f"Affected column indices: {below_threshold.tolist()}. "
            "Division by near-zero output would produce unreliable coefficients. "
            "Check the sectors DataFrame for missing or zero output values."
        )

    # Column-wise division: a_ij = z_ij / x_j
    A = Z / x[np.newaxis, :]

    if np.any(A > 1.0):
        over_one = list(zip(*np.where(A > 1.0)))
        warnings.warn(
            f"Direct requirements matrix A contains {len(over_one)} element(s) > 1.0. "
            "Values exceeding 1.0 mean a sector spends more than its gross output on a "
            "single input, which is economically implausible and may indicate data errors. "
            f"First few offending (row, col) indices: {over_one[:5]}",
            UserWarning,
            stacklevel=2,
        )

    return A


def calculate_employment_coefficients(sectors_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate FTE employment per dollar of gross output for each sector.

    employment_coeff = employment_fte / (output_millions * 1_000_000)

    Args:
        sectors_df: DataFrame with columns sector_id, sector_name,
            employment_fte, output_millions.

    Returns:
        DataFrame with columns: sector_id, sector_name, employment_coeff.
    """
    output_dollars = sectors_df["output_millions"] * 1_000_000.0
    coeff = sectors_df["employment_fte"] / output_dollars
    return pd.DataFrame(
        {
            "sector_id": sectors_df["sector_id"].values,
            "sector_name": sectors_df["sector_name"].values,
            "employment_coeff": coeff.values,
        }
    )


def calculate_jobs_per_million(sectors_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate FTE jobs per million dollars of gross output for each sector.

    jobs_per_million = employment_fte / output_millions

    Args:
        sectors_df: DataFrame with columns sector_id, sector_name,
            employment_fte, output_millions.

    Returns:
        DataFrame with columns: sector_id, sector_name, jobs_per_million.
    """
    jpm = sectors_df["employment_fte"] / sectors_df["output_millions"]
    return pd.DataFrame(
        {
            "sector_id": sectors_df["sector_id"].values,
            "sector_name": sectors_df["sector_name"].values,
            "jobs_per_million": jpm.values,
        }
    )
