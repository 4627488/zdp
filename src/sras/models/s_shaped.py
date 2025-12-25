"""Yamada S-shaped reliability growth model."""

from __future__ import annotations

import numpy as np
from scipy import optimize

from sras.data import FailureDataset, FailureSeriesType

from .base import ModelResult, ReliabilityModel


def _s_shaped_mean_value(t: np.ndarray, a: float, b: float) -> np.ndarray:
    return a * (1.0 - (1.0 + b * t) * np.exp(-b * t))


class SShapedModel(ReliabilityModel):
    name = "Yamada S-Shaped"
    required_series_type = FailureSeriesType.CUMULATIVE_FAILURES
    param_count = 2

    def __init__(self) -> None:
        self.a: float | None = None
        self.b: float | None = None

    def _fit(
        self,
        dataset: FailureDataset,
        *,
        evaluation_times: np.ndarray | None = None,
    ) -> ModelResult:
        time_axis = dataset.time_axis
        cumulative = dataset.cumulative_failures()

        params, _ = optimize.curve_fit(
            _s_shaped_mean_value,
            time_axis,
            cumulative,
            p0=(cumulative.max() * 1.1, 0.01),
            bounds=(0.0, np.inf),
            maxfev=20000,
        )
        self.a, self.b = map(float, params)
        eval_times = evaluation_times if evaluation_times is not None else time_axis
        predictions = _s_shaped_mean_value(eval_times, self.a, self.b)
        metrics = self.compute_metrics(cumulative, _s_shaped_mean_value(time_axis, self.a, self.b))
        return ModelResult(
            model_name=self.name,
            parameters={"a": self.a, "b": self.b},
            times=eval_times,
            predictions=predictions,
            metrics=metrics,
        )


__all__ = ["SShapedModel"]
