from typing import Optional, Callable
import numpy as np
from scipy.optimize import brentq, curve_fit, newton

from .base import ReliabilityModel


class JMModel(ReliabilityModel):
    """Jelinski-Moranda (JM) model for reliability prediction."""

    name: str
    N: Optional[float]
    phi: Optional[float]
    train_failures_count: int

    def __init__(self) -> None:
        super().__init__()
        self.name: str = "JM Model"
        self.N: Optional[float] = None
        self.phi: Optional[float] = None
        self.train_failures_count: int = 0

    def _jm_tbf_func(self, i: np.ndarray, N: float, phi: float) -> np.ndarray:
        """
        Expected TBF function for Least Squares fallback.
        E[TBF_i] = 1 / (phi * (N - i + 1))

        Args:
            i: Failure index array.
            N: Total number of faults parameter.
            phi: Fault detection rate parameter.

        Returns:
            Array of expected TBF values.
        """
        N = np.float64(N)
        phi = np.float64(phi)

        term: np.ndarray = N - i + 1
        denom: np.ndarray = phi * term

        result: np.ndarray = np.full_like(i, 1e10, dtype=np.float64)

        is_finite: np.ndarray = np.isfinite(denom)
        is_positive: np.ndarray = denom > 1e-9
        valid_mask: np.ndarray = is_finite & is_positive

        if np.any(valid_mask):
            val: np.ndarray = 1.0 / denom[valid_mask]
            result[valid_mask] = val

        return result

    def fit(self, tbf_train: np.ndarray) -> None:
        """
        Fit the Jelinski-Moranda model using Maximum Likelihood Estimation (MLE).
        Falls back to Least Squares if MLE fails.

        Args:
            tbf_train: Array of training time between failures.
        """
        mask: np.ndarray = (tbf_train > 1e-9) & np.isfinite(tbf_train)
        tbf: np.ndarray = tbf_train[mask]
        n: int = len(tbf)
        self.train_failures_count = n

        if n < 2:
            print("JM Model: Not enough data points to fit.")
            self.N, self.phi = None, None
            return

        # --- MLE Estimation ---
        Tn: float = np.sum(tbf)
        weighted_sum: float = np.sum(np.arange(n) * tbf)
        C: float = weighted_sum / Tn

        def mle_eq(N_val: float) -> float:
            """MLE equation: sum(1/(N-i+1)) - n/(N-C) = 0"""
            if N_val <= n - 1 + 1e-6:
                return 1e9

            if np.abs(N_val - C) < 1e-6:
                return -1e9

            denoms: np.ndarray = N_val - np.arange(n)

            if np.any(np.abs(denoms) < 1e-9):
                return 1e9

            sum_inv: float = np.sum(1.0 / denoms)
            term2: float = n / (N_val - C)
            return sum_inv - term2

        try:
            y_n: float = mle_eq(n)
            y_inf: float = mle_eq(n * 100)

            if np.isfinite(y_n) and np.isfinite(y_inf) and y_n * y_inf < 0:
                N_est: float = brentq(mle_eq, n, n * 100)
            else:
                N_est = newton(mle_eq, n + 0.1, maxiter=50)

            if N_est < n:
                raise ValueError("Estimated N < n")

            self.N = N_est
            self.phi = n / (self.N * Tn - weighted_sum)

        except Exception as e:
            print(f"JM Model MLE failed ({e}), falling back to Least Squares.")
            self._fit_least_squares(tbf, n)

    def _fit_least_squares(self, tbf: np.ndarray, n: int) -> None:
        """Fit JM model using Least Squares method.

        Args:
            tbf: Filtered time between failures array.
            n: Number of failures.
        """
        train_idx: np.ndarray = np.arange(1, n + 1)

        try:
            y: np.ndarray = 1.0 / tbf
            if not np.all(np.isfinite(y)):
                raise ValueError("Infinite values in transformed data")

            slope, intercept = np.polyfit(train_idx, y, 1)
            if slope < 0:
                phi0: float = -slope
                N0: float = (intercept / phi0) - 1
            else:
                phi0 = 1e-3
                N0 = n * 1.1
        except Exception:
            phi0 = 1e-3
            N0 = n * 1.1

        if N0 < n:
            N0 = n + 1

        try:
            popt, _ = curve_fit(
                self._jm_tbf_func,
                train_idx,
                tbf,
                p0=[N0, phi0],
                bounds=([n, 0], [np.inf, np.inf]),
                maxfev=2000,
            )
            self.N, self.phi = popt
        except Exception as e:
            print(f"JM Model Least Squares failed: {e}")
            self.N, self.phi = None, None

    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        """Predict cumulative failure times.

        Args:
            n_steps: Number of steps to predict.
            last_cumulative_time: The last cumulative failure time.

        Returns:
            Array of predicted cumulative times.
        """
        if self.N is None or self.phi is None:
            return np.full(n_steps, np.nan)

        start_i: int = self.train_failures_count + 1
        indices: np.ndarray = np.arange(start_i, start_i + n_steps)

        # TBF_i = 1 / (phi * (N - i + 1))
        denoms: np.ndarray = self.phi * (self.N - indices + 1)

        # Handle cases where N < i (all faults found)
        pred_tbf: np.ndarray = np.full(n_steps, np.inf)
        valid: np.ndarray = denoms > 1e-9
        pred_tbf[valid] = 1.0 / denoms[valid]

        return last_cumulative_time + np.cumsum(pred_tbf)
