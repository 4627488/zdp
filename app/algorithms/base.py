from abc import ABC, abstractmethod
import numpy as np
from typing import Tuple, List


class ReliabilityModel(ABC):
    def __init__(self):
        self.name = "Base Model"

    @abstractmethod
    def fit(self, tbf_train: np.ndarray) -> None:
        """
        Train the model using Time Between Failures (TBF) data.
        """
        pass

    @abstractmethod
    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        """
        Predict the cumulative time for the next n_steps failures.
        Returns an array of predicted cumulative times.
        """
        pass

    def get_name(self) -> str:
        return self.name
