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
        n = self.train_failures_count

        # 1. Try Linear Regression Approximation for Initial Guess
        # 1/TBF_i = phi(N+1) - phi*i = A + B*i
        # B = -phi, A = phi(N+1)
        try:
            # Filter out zero TBF for inversion (replace with small value)
            tbf_safe = np.where(tbf_train <= 0, 1e-6, tbf_train)
            y = 1.0 / tbf_safe
            
            # Polyfit degree 1
            B, A = np.polyfit(train_idx, y, 1)
            
            if B < 0: # Valid JM assumption (reliability growth)
                phi_est = -B
                N_est = (A / phi_est) - 1
                if N_est > n:
                    guesses = [[N_est, phi_est]]
                else:
                    guesses = []
            else:
                guesses = []
        except Exception:
            guesses = []

        # 2. Add standard guesses
        guesses.extend([
            [n * 1.1, 0.001],
            [n * 1.5, 0.01],
            [n * 2.0, 0.05],
            [n * 10.0, 0.0001],
            [n * 100.0, 1e-5] # Very reliable system
        ])
        
        # Bounds: N > observed failures
        bounds = ([n + 0.1, 0], [np.inf, 1])

        for p0 in guesses:
            try:
                popt, _ = curve_fit(
                    self._jm_tbf_func,
                    train_idx,
                    tbf_train,
                    p0=p0,
                    bounds=bounds,
                    maxfev=10000,
                )
                self.N, self.phi = popt
                return
            except Exception:
                continue
        
        # 3. Fallback: If curve_fit fails but we had a valid linear estimate, use it
        if len(guesses) > 0 and guesses[0][0] > n:
             print("JM Model: curve_fit failed, using linear estimate fallback.")
             self.N, self.phi = guesses[0]
             return

        print(f"JM Model fitting failed after {len(guesses)} attempts.")
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
