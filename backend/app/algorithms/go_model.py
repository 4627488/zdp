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

        # Initial guess and bounds as per main.py
        try:
            popt, _ = curve_fit(
                self._go_func,
                cumulative_time,
                failure_counts,
                p0=[len(tbf_train) * 1.2, 0.01],
                bounds=(0, [np.inf, 1]),
                maxfev=5000,
            )
            self.a, self.b = popt
        except Exception as e:
            print(f"GO Model fitting failed: {e}")
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
