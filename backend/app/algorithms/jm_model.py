import numpy as np
from scipy.optimize import curve_fit
from .base import ReliabilityModel


class JMModel(ReliabilityModel):
    def __init__(self):
        self.name = "JM Model"
        self.N = None
        self.phi = None
        self.train_failures_count = 0

    def _jm_tbf_func(self, i, N, phi):
        # Avoid division by zero or negative if N is estimated lower than i
        denom = phi * (N - i + 1)
        return np.where(denom <= 0, np.inf, 1.0 / denom)

    def fit(self, tbf_train: np.ndarray) -> None:
        self.train_failures_count = len(tbf_train)
        train_idx = np.arange(1, self.train_failures_count + 1)

        try:
            # Initial guess: N slightly larger than observed, phi small
            p0 = [self.train_failures_count * 1.5, 0.01]
            # Bounds: N > observed failures
            bounds = ([self.train_failures_count + 0.1, 0], [np.inf, 1])

            popt, _ = curve_fit(
                self._jm_tbf_func,
                train_idx,
                tbf_train,
                p0=p0,
                bounds=bounds,
                maxfev=5000,
            )
            self.N, self.phi = popt
        except Exception as e:
            print(f"JM Model fitting failed: {e}")
            self.N, self.phi = None, None

    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        if self.N is None or self.phi is None:
            return np.full(n_steps, np.nan)

        test_idx = np.arange(
            self.train_failures_count + 1, self.train_failures_count + n_steps + 1
        )
        pred_tbf = self._jm_tbf_func(test_idx, self.N, self.phi)

        # Handle potential infinites if N < test_idx
        pred_tbf = np.nan_to_num(pred_tbf, nan=np.nan, posinf=np.nan)

        # Cumulative sum added to the last known time
        pred_cumulative = last_cumulative_time + np.cumsum(pred_tbf)
        return pred_cumulative
