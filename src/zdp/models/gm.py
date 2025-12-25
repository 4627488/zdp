"""Grey Model GM(1,1) for cumulative failure prediction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from zdp.data import FailureDataset, FailureSeriesType

from .base import ModelResult, ReliabilityModel


@dataclass
class GMConfig:
    """Configuration for GM(1,1). Currently no tunables, kept for symmetry."""
    pass


class GM11Model(ReliabilityModel):
    name = "GM(1,1)"
    required_series_type = FailureSeriesType.CUMULATIVE_FAILURES
    param_count = 2  # a, b

    def __init__(self, config: GMConfig | None = None) -> None:
        self.config = config or GMConfig()
        self.a: float | None = None
        self.b: float | None = None

    @staticmethod
    def _fit_parameters(x0: np.ndarray) -> tuple[float, float]:
        # 1-AGO cumulative sequence
        x1 = np.cumsum(x0)
        # mean sequence z1(k) = 0.5*(x1(k) + x1(k-1)), k=2..n
        z1 = 0.5 * (x1[1:] + x1[:-1])
        # GM(1,1): x0(k) + a * z1(k) = b, for k=2..n
        # Solve [a, b]^T via least squares
        B = np.column_stack((-z1, np.ones_like(z1)))
        Y = x0[1:]
        theta, *_ = np.linalg.lstsq(B, Y, rcond=None)
        a, b = float(theta[0]), float(theta[1])
        return a, b

    @staticmethod
    def _predict_cumulative(x1_1: float, a: float, b: float, n: int) -> np.ndarray:
        # x1(k) = (x1(1) - b/a) * exp(-a*(k-1)) + b/a
        # Ensure numerical stability when a ~ 0
        eps = 1e-12
        if abs(a) < eps:
            # When a -> 0, x1(k) ~ x1(1) + (k-1) * b
            return x1_1 + b * np.arange(n, dtype=float)
        const = x1_1 - b / a
        k = np.arange(n, dtype=float)
        return const * np.exp(-a * k) + b / a

    def _fit(
        self,
        dataset: FailureDataset,
        *,
        evaluation_times: np.ndarray | None = None,
    ) -> ModelResult:
        time_axis = dataset.time_axis
        cumulative = dataset.cumulative_failures()
        n = cumulative.size
        if n < 3:
            # Not enough points for a robust GM(1,1) fit
            predictions = cumulative.copy()
            self.a, self.b = float("nan"), float("nan")
        else:
            # Derive x0 (increments) from cumulative
            x0 = np.diff(np.concatenate([[0.0], cumulative]))
            a, b = self._fit_parameters(x0)
            self.a, self.b = a, b
            x1_pred = self._predict_cumulative(cumulative[0], a, b, n)
            # GM(1,1) cumulative predictions should be non-decreasing
            predictions = np.maximum.accumulate(x1_pred)
        eval_times = evaluation_times if evaluation_times is not None else time_axis
        metrics = self.compute_metrics(cumulative, predictions)
        return ModelResult(
            model_name=self.name,
            parameters={"a": float(self.a or float("nan")), "b": float(self.b or float("nan"))},
            times=np.asarray(eval_times, dtype=float),
            predictions=np.asarray(predictions, dtype=float),
            metrics=metrics,
        )


__all__ = ["GM11Model", "GMConfig"]
