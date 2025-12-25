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

        if p <= threshold:
            # Standard JM MLE condition: no finite solution exists.
            raise RuntimeError(
                f"JM has no finite MLE solution for this dataset (P={p:.6f} <= (n-1)/2={threshold:.6f})."
            )

        def mle_eq(N: float) -> float:
            k = np.arange(n, dtype=float)
            term1 = np.sum(1.0 / (N - k))
            term2 = n / (N - p)
            return term1 - term2

        # Bisection-style solve, mirroring the typical teaching implementation.
        ex = 1e-6
        ey = 1e-6
        left = (n - 1) + 1e-6
        right = max(float(n), left + 1.0)

        f_right = mle_eq(right)
        steps = 0
        while f_right > ey:
            left = right
            right = right + 1.0
            f_right = mle_eq(right)
            steps += 1
            if steps > 200000:
                raise RuntimeError("JM root search failed to bracket a solution within iteration limit")

        # If we've landed close enough, accept right as the root.
        if -ey <= f_right <= ey:
            self.n0 = float(right)
        else:
            # Now f(left) should be > ey and f(right) <= ey; bisect until convergence.
            for _ in range(200000):
                if abs(right - left) <= ex:
                    self.n0 = float((right + left) / 2.0)
                    break
                mid = (right + left) / 2.0
                f_mid = mle_eq(mid)
                if f_mid > ey:
                    left = mid
                elif f_mid < -ey:
                    right = mid
                else:
                    self.n0 = float(mid)
                    break
            else:
                raise RuntimeError("JM bisection failed to converge")

        denom = self.n0 * total_time - weighted_time
        if denom <= 0:
            raise RuntimeError("JM failed to compute phi due to non-positive denominator")
        self.phi = n / denom

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
