import numpy as np
from scipy.optimize import curve_fit
from .base import ReliabilityModel


class GOModel(ReliabilityModel):
    def __init__(self):
        self.name = "GO Model (NHPP)"
        self.a = None
        self.b = None
        self.train_failures_count = 0

    def _go_func(self, t, a, b):
        return a * (1 - np.exp(-b * t))

    def fit(self, tbf_train: np.ndarray) -> None:
        cumulative_time = np.cumsum(tbf_train)
        failure_counts = np.arange(1, len(tbf_train) + 1)
        self.train_failures_count = len(tbf_train)

        # Try multiple initial guesses to improve convergence
        # a (total failures) > current failures
        # b (rate) usually small
        n = len(tbf_train)
        guesses = [
            [n * 1.1, 0.001],
            [n * 1.2, 0.01],
            [n * 1.5, 0.05],
            [n * 2.0, 0.1],
            [n * 5.0, 0.0001]
        ]

        for p0 in guesses:
            try:
                popt, _ = curve_fit(
                    self._go_func,
                    cumulative_time,
                    failure_counts,
                    p0=p0,
                    bounds=(0, [np.inf, 1]),
                    maxfev=10000,
                )
                self.a, self.b = popt
                # If we found a solution, stop trying
                return
            except Exception:
                continue
        
        # If all guesses fail
        print(f"GO Model fitting failed after {len(guesses)} attempts.")
        self.a, self.b = None, None

    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        if self.a is None or self.b is None:
            return np.full(n_steps, np.nan)

        predictions = []
        start_failure = self.train_failures_count + 1

        for i in range(n_steps):
            y_target = start_failure + i
            # t = -ln(1 - y/a) / b
            if y_target >= self.a:
                predictions.append(np.nan)
            else:
                pred_t = -np.log(1 - y_target / self.a) / self.b
                predictions.append(pred_t)

        return np.array(predictions)
