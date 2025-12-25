from typing import Any, Optional
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler

from .base import ReliabilityModel


class BPModel(ReliabilityModel):
    """BP Neural Network model for reliability prediction."""

    name: str
    window_size: int
    scaler: MinMaxScaler
    model: MLPRegressor
    last_window: Optional[np.ndarray]
    tbf_scaled: Optional[np.ndarray]

    def __init__(self, window_size: int = 3) -> None:
        self.name: str = "BP Neural Network"
        self.window_size: int = window_size
        self.scaler: MinMaxScaler = MinMaxScaler(feature_range=(0, 1))
        self.model: MLPRegressor = MLPRegressor(
            hidden_layer_sizes=(16, 8),
            activation="relu",
            solver="lbfgs",
            max_iter=5000,
            random_state=42,
        )
        self.last_window: Optional[np.ndarray] = None
        self.tbf_scaled: Optional[np.ndarray] = None

    def _create_dataset(self, dataset: np.ndarray, look_back: int = 1) -> tuple[np.ndarray, np.ndarray]:
        """Create dataset for training.

        Args:
            dataset: Input data array.
            look_back: Number of previous timesteps to use as input variables.

        Returns:
            Tuple of (dataX, dataY) arrays.
        """
        dataX: list[np.ndarray] = []
        dataY: list[np.ndarray] = []
        for i in range(len(dataset) - look_back):
            dataX.append(dataset[i : (i + look_back)])
            dataY.append(dataset[i + look_back])
        return np.array(dataX), np.array(dataY)

    def fit(self, tbf_train: np.ndarray) -> None:
        """Fit the BP Neural Network model.

        Args:
            tbf_train: Array of training time between failures.

        Raises:
            ValueError: If not enough data for the specified window size.
        """
        # Scale data
        tbf_reshaped: np.ndarray = np.array(tbf_train).reshape(-1, 1)
        self.tbf_scaled = self.scaler.fit_transform(tbf_reshaped).flatten()  # type: ignore[no-untyped-call]

        if len(self.tbf_scaled) <= self.window_size:
            raise ValueError("Not enough data for the specified window size")

        trainX, trainY = self._create_dataset(self.tbf_scaled, self.window_size)
        self.model.fit(trainX, trainY)

        # Store last window for prediction
        self.last_window = self.tbf_scaled[-self.window_size :].reshape(1, -1)

    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        """Predict cumulative failure times.

        Args:
            n_steps: Number of steps to predict.
            last_cumulative_time: The last cumulative failure time.

        Returns:
            Array of predicted cumulative times.
        """
        if self.last_window is None:
            return np.full(n_steps, np.nan)

        curr_input: np.ndarray = self.last_window.copy()
        pred_tbf_scaled: list[np.ndarray] = []

        # Recursive prediction (using predicted value as input for next)
        for _ in range(n_steps):
            pred: np.ndarray = self.model.predict(curr_input)
            pred_val: np.floating[Any] = pred[0]
            pred_tbf_scaled.append(np.array([pred_val]))

            # Update window: remove first, add new prediction
            curr_input = np.append(curr_input[0][1:], pred_val).reshape(1, -1)

        # Inverse transform
        pred_tbf: np.ndarray = self.scaler.inverse_transform(
            np.array(pred_tbf_scaled).reshape(-1, 1)
        ).flatten()

        # Ensure TBF is positive (physically impossible to have negative time between failures)
        pred_tbf = np.maximum(pred_tbf, 1e-6)

        pred_cumulative: np.ndarray = last_cumulative_time + np.cumsum(pred_tbf)
        return pred_cumulative
