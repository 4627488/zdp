"""BP neural network model implemented with PyTorch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import torch
from torch import Tensor, nn

from zdp.data import FailureDataset, FailureSeriesType

from .base import ModelResult, ReliabilityModel


def _normalize(values: np.ndarray) -> tuple[np.ndarray, float, float]:
    v_min = float(values.min())
    v_max = float(values.max())
    span = v_max - v_min
    if span == 0:
        return np.zeros_like(values), v_min, span
    return (values - v_min) / span, v_min, span


def _denormalize(values: np.ndarray, v_min: float, span: float) -> np.ndarray:
    if span == 0:
        return np.full_like(values, v_min)
    return values * span + v_min


@dataclass
class BPConfig:
    hidden_size: int = 16
    epochs: int = 800
    learning_rate: float = 0.01
    momentum: float = 0.9
    train_split: float = 0.8


class BPNeuralNetworkModel(ReliabilityModel):
    name = "BP Neural Network"
    required_series_type = FailureSeriesType.CUMULATIVE_FAILURES

    def __init__(self, config: BPConfig | None = None) -> None:
        self.config = config or BPConfig()
        self.loss_curve: list[float] = []
        self.param_count = 3 * self.config.hidden_size + 1

    def _build_network(self) -> nn.Module:
        return nn.Sequential(
            nn.Linear(1, self.config.hidden_size),
            nn.Sigmoid(),
            nn.Linear(self.config.hidden_size, 1),
        )

    def _fit(
        self,
        dataset: FailureDataset,
        *,
        evaluation_times: np.ndarray | None = None,
    ) -> ModelResult:
        time_axis = dataset.time_axis.astype(np.float32)
        targets = dataset.cumulative_failures().astype(np.float32)
        x_norm, x_min, x_span = _normalize(time_axis)
        y_norm, y_min, y_span = _normalize(targets)
        x_norm = x_norm.reshape(-1, 1)
        y_norm = y_norm.reshape(-1, 1)

        split_idx = max(2, int(len(x_norm) * self.config.train_split))
        train_x = torch.tensor(x_norm[:split_idx], dtype=torch.float32)
        train_y = torch.tensor(y_norm[:split_idx], dtype=torch.float32)
        val_x = torch.tensor(x_norm, dtype=torch.float32)

        network = self._build_network()
        criterion = nn.MSELoss()
        optimizer = torch.optim.SGD(
            network.parameters(), lr=self.config.learning_rate, momentum=self.config.momentum
        )

        self.loss_curve = []
        for _ in range(self.config.epochs):
            optimizer.zero_grad()
            outputs = network(train_x)
            loss: Tensor = criterion(outputs, train_y)
            loss.backward()
            optimizer.step()
            self.loss_curve.append(float(loss.detach().cpu().item()))

        with torch.no_grad():
            preds = network(val_x).cpu().numpy().reshape(-1)
        predictions = _denormalize(preds, y_min, y_span)
        eval_times = evaluation_times if evaluation_times is not None else time_axis
        metrics = self.compute_metrics(targets, predictions)
        diagnostics = {"loss_curve": self.loss_curve[-50:]}
        return ModelResult(
            model_name=self.name,
            parameters={
                "hidden_size": float(self.config.hidden_size),
                "epochs": float(self.config.epochs),
                "lr": float(self.config.learning_rate),
            },
            times=eval_times,
            predictions=predictions,
            metrics=metrics,
            diagnostics=diagnostics,
        )


__all__ = ["BPNeuralNetworkModel", "BPConfig"]
