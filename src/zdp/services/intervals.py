"""Prediction interval helpers."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
from scipy import stats


def normal_prediction_interval(
    actual: np.ndarray,
    predicted: np.ndarray,
    *,
    alpha: float = 0.05,
) -> tuple[np.ndarray, np.ndarray, Mapping[str, Any]]:
    """Compute a simple normal-approximation prediction interval.

    Uses residual standard deviation from in-sample fit:

        y_hat ± z_(1-alpha/2) * sigma_hat

    Returns:
        lower, upper, diagnostics
    """

    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    if actual.shape != predicted.shape:
        raise ValueError("Actual and predicted arrays must align")

    alpha = float(alpha)
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be between 0 and 1")

    residuals = actual - predicted
    sigma = float(np.std(residuals, ddof=1)) if residuals.size > 1 else float(np.std(residuals, ddof=0))
    z = float(stats.norm.ppf(1.0 - alpha / 2.0))
    half = z * sigma

    lower = predicted - half
    upper = predicted + half
    diag: dict[str, Any] = {"method": "normal", "alpha": alpha, "sigma": sigma, "z": z}
    return lower, upper, diag


__all__ = ["normal_prediction_interval"]
