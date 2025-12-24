
from .base import ReliabilityModel
import numpy as np

class StatisticalModel(ReliabilityModel):
    def __init__(self):
        self.name = "Statistical (Linear)"
        self.slope = 0
        self.intercept = 0

    def fit(self, tbf_train: np.ndarray) -> None:
        # Simple Linear Regression on cumulative time
        n = len(tbf_train)
        X = np.arange(n).reshape(-1, 1)
        y = np.cumsum(tbf_train)
        
        # y = mx + c
        # Using numpy polyfit for simplicity
        if n > 1:
            self.slope, self.intercept = np.polyfit(X.flatten(), y, 1)
        else:
            self.slope = y[0] if n > 0 else 0
            self.intercept = 0

    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        # Predict next n_steps
        # We continue the trend
        # Current step count is implicitly handled by continuing the line
        # But wait, we need to know the current 'x' (failure number)
        # This simple model assumes linear growth of cumulative time (constant failure rate)
        
        # Actually, let's do something slightly smarter: Moving Average of TBF
        # This is a "Statistical" baseline
        return np.array([last_cumulative_time + (i + 1) * self.slope for i in range(n_steps)])

class BayesianModel(ReliabilityModel):
    def __init__(self):
        self.name = "Bayesian (Simple)"
        self.lambda_ = 0.1

    def fit(self, tbf_train: np.ndarray) -> None:
        # Estimate lambda (rate parameter) using Bayesian update with Gamma prior
        # Prior: Gamma(alpha=1, beta=1)
        # Posterior: Gamma(alpha + n, beta + sum(tbf))
        # Expected lambda = (alpha + n) / (beta + sum(tbf))
        
        alpha_prior = 1.0
        beta_prior = 1.0
        
        n = len(tbf_train)
        sum_tbf = np.sum(tbf_train)
        
        alpha_post = alpha_prior + n
        beta_post = beta_prior + sum_tbf
        
        self.lambda_ = alpha_post / beta_post if beta_post > 0 else 0.1

    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        # Expected TBF is 1/lambda
        expected_tbf = 1.0 / self.lambda_ if self.lambda_ > 0 else 1.0
        
        predictions = []
        current_time = last_cumulative_time
        for _ in range(n_steps):
            current_time += expected_tbf
            predictions.append(current_time)
            
        return np.array(predictions)
