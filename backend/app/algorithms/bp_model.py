import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from .base import ReliabilityModel


class BPModel(ReliabilityModel):
    def __init__(self, window_size=3):
        self.name = "BP Neural Network"
        self.window_size = window_size
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = MLPRegressor(
            hidden_layer_sizes=(16, 8),
            activation="relu",
            solver="lbfgs",
            max_iter=5000,
            random_state=42,
        )
        self.last_window = None

    def _create_dataset(self, dataset, look_back=1):
        dataX, dataY = [], []
        for i in range(len(dataset) - look_back):
            dataX.append(dataset[i : (i + look_back)])
            dataY.append(dataset[i + look_back])
        return np.array(dataX), np.array(dataY)

    def fit(self, tbf_train: np.ndarray) -> None:
        # Scale data
        tbf_reshaped = np.array(tbf_train).reshape(-1, 1)
        self.tbf_scaled = self.scaler.fit_transform(tbf_reshaped).flatten()

        if len(self.tbf_scaled) <= self.window_size:
            raise ValueError("Not enough data for the specified window size")

        trainX, trainY = self._create_dataset(self.tbf_scaled, self.window_size)
        self.model.fit(trainX, trainY)

        # Store last window for prediction
        self.last_window = self.tbf_scaled[-self.window_size :].reshape(1, -1)

    def predict(self, n_steps: int, last_cumulative_time: float) -> np.ndarray:
        if self.last_window is None:
            return np.full(n_steps, np.nan)

        curr_input = self.last_window.copy()
        pred_tbf_scaled = []

        # Recursive prediction (using predicted value as input for next)
        # Note: main.py used "Teacher Forcing" (using real values) for the test set because it had them.
        # In a real prediction scenario, we don't have the future real values, so we must use our own predictions.
        # However, the user request implies "predict and compare with split test set".
        # If we want to strictly follow main.py's logic for evaluation, we need the test set ground truth passed in.
        # But for a general "predict" interface, we should assume we don't know the future.
        # I will implement the standard recursive prediction here.
        # If the user wants evaluation, the backend logic will handle passing ground truth if available,
        # but the model interface should probably be pure prediction.

        for _ in range(n_steps):
            pred = self.model.predict(curr_input)
            pred_val = pred[0]
            pred_tbf_scaled.append(pred_val)

            # Update window: remove first, add new prediction
            curr_input = np.append(curr_input[0][1:], pred_val).reshape(1, -1)

        # Inverse transform
        pred_tbf = self.scaler.inverse_transform(
            np.array(pred_tbf_scaled).reshape(-1, 1)
        ).flatten()

        # Ensure TBF is positive (physically impossible to have negative time between failures)
        pred_tbf = np.maximum(pred_tbf, 1e-6)

        pred_cumulative = last_cumulative_time + np.cumsum(pred_tbf)
        return pred_cumulative
