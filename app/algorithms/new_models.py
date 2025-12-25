from typing import Optional
import numpy as np

from .base import ReliabilityModel


class StatisticalModel(ReliabilityModel):
    """Statistical (Linear) model for reliability prediction."""

    name: str
    slope: float
    intercept: float

    def __init__(self) -> None:
        self.name: str = "Statistical (Linear)"
        self.slope: float = 0.0
        self.intercept: float = 0.0

    def fit(self, tbf_train: np.ndarray) -> None:
        """Fit the statistical model using linear regression.

        Args:
            tbf_train: Array of training time between failures.
        """
        n: int = len(tbf_train)
        X: np.ndarray = np.arange(n).reshape(-1, 1)
        y: np.ndarray = np.cumsum(tbf_train)
        
        # y = mx + c
        if n > 1:
            self.slope, self.intercept = np.polyfit(X.flatten(), y, 1)
        else:
            self.slope = y[0] if n > 0 else 0.0
            self.intercept = 0.0

    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        """Predict cumulative failure times.

        Args:
            n_steps: Number of steps to predict.
            last_cumulative_time: The last cumulative failure time.

        Returns:
            Array of predicted cumulative times.
        """
        return np.array([last_cumulative_time + (i + 1) * self.slope for i in range(n_steps)])


class BayesianModel(ReliabilityModel):
    """Bayesian (Simple) model for reliability prediction."""

    name: str
    lambda_: float

    def __init__(self) -> None:
        self.name: str = "Bayesian (Simple)"
        self.lambda_: float = 0.1

    def fit(self, tbf_train: np.ndarray) -> None:
        """Fit the Bayesian model using Gamma prior.

        Estimate lambda (rate parameter) using Bayesian update with Gamma prior.
        Prior: Gamma(alpha=1, beta=1)
        Posterior: Gamma(alpha + n, beta + sum(tbf))
        Expected lambda = (alpha + n) / (beta + sum(tbf))

        Args:
            tbf_train: Array of training time between failures.
        """
        alpha_prior: float = 1.0
        beta_prior: float = 1.0
        
        n: int = len(tbf_train)
        sum_tbf: float = np.sum(tbf_train)
        
        alpha_post: float = alpha_prior + n
        beta_post: float = beta_prior + sum_tbf
        
        self.lambda_ = alpha_post / beta_post if beta_post > 0 else 0.1

    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        """Predict cumulative failure times.

        Args:
            n_steps: Number of steps to predict.
            last_cumulative_time: The last cumulative failure time.

        Returns:
            Array of predicted cumulative times.
        """
        expected_tbf: float = 1.0 / self.lambda_ if self.lambda_ > 0 else 1.0
        
        predictions: list[float] = []
        current_time: float = last_cumulative_time
        for _ in range(n_steps):
            current_time += expected_tbf
            predictions.append(current_time)
            
        return np.array(predictions)
