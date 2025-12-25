"""Support Vector Regression reliability model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from zdp.data import FailureDataset, FailureSeriesType

from .base import ModelResult, ReliabilityModel


@dataclass
class SVRConfig:
    kernel: str = "rbf"
    c: float = 10.0
    epsilon: float = 0.01
    gamma: str = "scale"


class SupportVectorRegressionModel(ReliabilityModel):
    name = "SVR"
    required_series_type = FailureSeriesType.CUMULATIVE_FAILURES
    param_count = 4

    def __init__(self, config: SVRConfig | None = None) -> None:
        self.config = config or SVRConfig()
        self._pipeline: Pipeline | None = None

    def _fit(
        self,
        dataset: FailureDataset,
        *,
        evaluation_times: np.ndarray | None = None,
    ) -> ModelResult:
        time_axis = dataset.time_axis.reshape(-1, 1)
        targets = dataset.cumulative_failures()
        pipeline = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "svr",
                    SVR(
                        kernel=self.config.kernel,
                        C=self.config.c,
                        epsilon=self.config.epsilon,
                        gamma=self.config.gamma,
                    ),
                ),
            ]
        )
        pipeline.fit(time_axis, targets)
        eval_times = evaluation_times if evaluation_times is not None else dataset.time_axis
        eval_times = np.asarray(eval_times, dtype=float)
        predictions = pipeline.predict(eval_times.reshape(-1, 1))
        self._pipeline = pipeline
        metrics = self.compute_metrics(targets, pipeline.predict(time_axis))
        return ModelResult(
            model_name=self.name,
            parameters={
                "kernel": self.config.kernel,
                "C": self.config.c,
                "epsilon": self.config.epsilon,
            },
            times=eval_times,
            predictions=predictions,
            metrics=metrics,
        )


__all__ = ["SupportVectorRegressionModel", "SVRConfig"]
