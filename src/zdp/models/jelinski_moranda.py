"""Implementation of the Jelinski-Moranda reliability growth model."""

from __future__ import annotations

import numpy as np
from scipy import optimize

from zdp.data import FailureDataset, FailureSeriesType

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
        n = intervals.size
        if n < 2:
            raise RuntimeError("JM model requires at least 2 failures")

        total_time = float(np.sum(intervals))
        if total_time <= 0:
            raise RuntimeError("JM model requires positive time intervals")

        # Statistic p = sum((i-1)*x_i) / sum(x_i), i from 1..n (0-based index used here)
        indices_0 = np.arange(n, dtype=float)
        weighted_time = float(np.sum(indices_0 * intervals))
        p = weighted_time / total_time

        # Existence condition for finite N0: p > (n-1)/2
        threshold = (n - 1) / 2.0

        def mle_eq(N: float) -> float:
            k = np.arange(n, dtype=float)
            term1 = np.sum(1.0 / (N - k))
            term2 = n / (N - p)
            return term1 - term2

        if p <= threshold:
            # No growth detectable; degrade to near-constant rate with large N0
            self.n0 = float(n * 1e6)
            denom = self.n0 * total_time - weighted_time
            self.phi = n / max(denom, 1e-12)
        else:
            lower = n - 1 + 1e-6
            upper = lower * 2.0
            for _ in range(80):
                if mle_eq(upper) < 0:
                    break
                lower = upper
                upper *= 2.0
            try:
                root = optimize.brentq(mle_eq, lower, upper)
                self.n0 = float(root)
            except ValueError:
                # Fallback if bracketing fails: use large N0 to avoid negative lambdas
                self.n0 = float(n * 1e6)
            denom = self.n0 * total_time - weighted_time
            self.phi = n / max(denom, 1e-12)

        predictions = self._expected_intervals(n)
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
        lambdas = np.maximum(lambdas, 1e-12)  # clamp to avoid negatives/zeros
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
