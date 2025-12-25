from abc import ABC, abstractmethod
import numpy as np

class ReliabilityModel(ABC):
    """Abstract base class for reliability prediction models."""

    name: str

    def __init__(self) -> None:
        self.name: str = "Base Model"

    @abstractmethod
    def fit(self, tbf_train: np.ndarray) -> None:
        """
        Train the model using Time Between Failures (TBF) data.

        Args:
            tbf_train: Array of time between failures for training.
        """
        pass

    @abstractmethod
    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        """
        Predict the cumulative time for the next n_steps failures.

        Args:
            n_steps: Number of failure steps to predict.
            last_cumulative_time: The last cumulative failure time.

        Returns:
            Array of predicted cumulative times.
        """
        pass

    def get_name(self) -> str:
        """Get the model name.

        Returns:
            The name of the model.
        """
        return self.name
