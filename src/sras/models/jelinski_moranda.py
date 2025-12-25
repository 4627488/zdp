"""Implementation of the Jelinski-Moranda reliability growth model."""

from __future__ import annotations

import numpy as np
from scipy import optimize

from sras.data import FailureDataset, FailureSeriesType

from .base import ModelResult, ReliabilityModel


class JelinskiMorandaModel(ReliabilityModel):
    name = "Jelinski-Moranda"
    required_series_type = FailureSeriesType.TIME_BETWEEN_FAILURES

    def __init__(self) -> None:
        self.n0: float | None = None
        self.phi: float | None = None

    def _fit(
        self,
        dataset: FailureDataset,
        *,
        evaluation_times: np.ndarray | None = None,
    ) -> ModelResult:
        intervals = dataset.failure_intervals()
        n_failures = intervals.size
        initial_guess = np.array([max(n_failures + 5.0, n_failures * 1.2), 1.0 / intervals.mean()])

        result = optimize.minimize(
            self._neg_log_likelihood,
            initial_guess,
            args=(intervals,),
            bounds=((n_failures + 1.0, None), (1e-9, None)),
            method="L-BFGS-B",
        )
        if not result.success:
            raise RuntimeError(f"JM optimization failed: {result.message}")

        self.n0, self.phi = result.x
        predictions = self._expected_intervals(n_failures)
        metrics = self.compute_metrics(intervals, predictions)
        times = dataset.time_axis if evaluation_times is None else evaluation_times
        return ModelResult(
            model_name=self.name,
            parameters={"N0": float(self.n0), "phi": float(self.phi)},
            times=times,
            predictions=predictions,
            metrics=metrics,
        )

    def _expected_intervals(self, count: int) -> np.ndarray:
        if self.n0 is None or self.phi is None:
            raise RuntimeError("Model must be fitted before predicting intervals")
        indices = np.arange(1, count + 1)
        lambdas = self.phi * (self.n0 - indices + 1)
        return 1.0 / lambdas

    @staticmethod
    def _neg_log_likelihood(params: np.ndarray, intervals: np.ndarray) -> float:
        n0, phi = params
        n = intervals.size
        if n0 <= n or phi <= 0:
            return np.inf
        indices = np.arange(1, n + 1)
        lambdas = phi * (n0 - indices + 1)
        if np.any(lambdas <= 0):
            return np.inf
        log_likelihood = np.sum(np.log(lambdas) - lambdas * intervals)
        return -float(log_likelihood)


__all__ = ["JelinskiMorandaModel"]
