"""Leontief I-O model for the CypressBit Transportation I-O Modeling Lab.

Implements the Leontief inverse and scenario solve step:

    L = (I - A)^{-1}                  (Leontief inverse)
    total_output = L @ f               (gross output for final demand f)
    indirect_output = L @ f - f        (supply-chain contribution only)

The class exposes both the explicit inverse (for documentation and matrix
inspection) and numpy.linalg.solve (preferred for scenario calculations
because it avoids explicit matrix inversion and is more numerically stable).

Reference: Section 6.2 of the CypressBit Transportation I-O Modeling Lab
build instructions.
"""

from __future__ import annotations

import numpy as np
import scipy.linalg

from . import config


def check_invertibility(A: np.ndarray) -> None:
    """Raise ValueError if (I - A) is singular or numerically ill-conditioned.

    Args:
        A: (n, n) direct requirements matrix.

    Raises:
        ValueError: If (I - A) is singular (determinant ≈ 0) or its condition
            number exceeds config.MAX_CONDITION_NUMBER.
    """
    n = A.shape[0]
    I_minus_A = np.eye(n) - A

    det = float(scipy.linalg.det(I_minus_A))
    if abs(det) < 1e-14:
        raise ValueError(
            f"(I - A) is singular: determinant is {det:.3e}. "
            "The Leontief inverse does not exist. "
            "Check for structural zeros or linearly dependent rows in the A matrix."
        )

    cond = float(np.linalg.cond(I_minus_A))
    if cond > config.MAX_CONDITION_NUMBER:
        raise ValueError(
            f"(I - A) is numerically ill-conditioned: condition number {cond:.3e} "
            f"exceeds MAX_CONDITION_NUMBER ({config.MAX_CONDITION_NUMBER:.3e}). "
            "Results would be unreliable. "
            "Verify the A matrix does not contain near-collinear rows or extreme values."
        )


class LeontiefModel:
    """Encapsulates the Leontief I-O model for a fixed set of sectors.

    Args:
        A: (n, n) direct requirements matrix (technical coefficients).
        sector_ids: Ordered list of n sector identifier strings.  Position i
            in this list corresponds to row/column i of A.

    Raises:
        ValueError: If A is not square, sector_ids length does not match A,
            or (I - A) fails the invertibility check.
    """

    def __init__(self, A: np.ndarray, sector_ids: list[str]) -> None:
        if A.ndim != 2 or A.shape[0] != A.shape[1]:
            raise ValueError(
                f"A must be a square 2-D array; got shape {A.shape}"
            )
        n = A.shape[0]
        if len(sector_ids) != n:
            raise ValueError(
                f"sector_ids has {len(sector_ids)} entries but A has {n} rows/columns. "
                "They must match."
            )

        check_invertibility(A)

        self.A = A
        self.sector_ids = list(sector_ids)
        self.I_minus_A: np.ndarray = np.eye(n) - A

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def n_sectors(self) -> int:
        """Number of sectors in the model."""
        return self.A.shape[0]

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def leontief_inverse(self) -> np.ndarray:
        """Compute and return the Leontief inverse L = (I - A)^{-1}.

        The explicit inverse is exposed for inspection, reporting, and
        multiplier analysis.  For scenario output calculations, prefer
        :meth:`solve`, which is more numerically stable.

        Returns:
            L (n, n) float64 array.

        Raises:
            ValueError: If (I - A) is singular at inversion time.
        """
        try:
            return np.linalg.inv(self.I_minus_A)
        except np.linalg.LinAlgError as exc:
            raise ValueError(
                "numpy.linalg.inv failed: (I - A) is singular. "
                "This should have been caught by check_invertibility at construction time. "
                f"Original error: {exc}"
            ) from exc

    def solve(self, final_demand: np.ndarray) -> np.ndarray:
        """Solve (I - A) @ output = final_demand for total output.

        Uses numpy.linalg.solve rather than explicit matrix inversion,
        which is more numerically stable for scenario calculations.

        Args:
            final_demand: (n,) array of final demand in dollars, one entry
                per sector in the same order as sector_ids.

        Returns:
            total_output (n,) array of gross output in dollars.

        Raises:
            ValueError: If final_demand does not have shape (n,).
        """
        if final_demand.ndim != 1 or final_demand.shape[0] != self.n_sectors:
            raise ValueError(
                f"final_demand must be a 1-D array of length {self.n_sectors}; "
                f"got shape {final_demand.shape}"
            )
        try:
            return np.linalg.solve(self.I_minus_A, final_demand)
        except np.linalg.LinAlgError as exc:
            raise ValueError(
                f"numpy.linalg.solve failed: {exc}"
            ) from exc

    def indirect_output(self, final_demand: np.ndarray) -> np.ndarray:
        """Return the supply-chain (indirect) output effect for a final demand vector.

        indirect_output = total_output - final_demand
                        = (L @ f) - f
                        = (L - I) @ f

        Args:
            final_demand: (n,) array of final demand in dollars.

        Returns:
            indirect_output (n,) array of indirect output in dollars.
        """
        return self.solve(final_demand) - final_demand
