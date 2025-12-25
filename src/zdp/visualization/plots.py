"""Matplotlib plot builders for ZDP."""

from __future__ import annotations

from typing import Sequence

import numpy as np
from matplotlib.figure import Figure

from zdp.data import FailureDataset, FailureSeriesType
from zdp.services.analysis import RankedModelResult


def _actual_series(dataset: FailureDataset) -> np.ndarray:
    if dataset.series_type == FailureSeriesType.CUMULATIVE_FAILURES:
        return dataset.cumulative_failures()
    return dataset.failure_intervals()


def _ensure_array(values: Sequence[float] | np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=float)


def plot_prediction_overview(
    figure: Figure,
    dataset: FailureDataset,
    ranked_results: Sequence[RankedModelResult],
    *,
    max_models: int = 3,
) -> None:
    ax = figure.add_subplot(111)
    actual = _actual_series(dataset)
    ax.plot(dataset.time_axis, actual, "o", label="Actual", color="#222222")
    for ranked in ranked_results[:max_models]:
        ax.plot(
            ranked.result.times,
            ranked.result.predictions,
            label=f"{ranked.rank}. {ranked.result.model_name}",
        )
    ax.set_xlabel("Time")
    ax.set_ylabel("Failures")
    ax.set_title("Model Prediction Overview")
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend(loc="best")


def plot_residuals(figure: Figure, dataset: FailureDataset, result: RankedModelResult) -> None:
    ax = figure.add_subplot(111)
    actual = _actual_series(dataset)
    predictions = _ensure_array(result.result.predictions)
    length = min(actual.size, predictions.size)
    residuals = actual[:length] - predictions[:length]
    ax.bar(dataset.time_axis[:length], residuals, color="#d95f02")
    ax.axhline(0.0, color="#555555", linestyle="--")
    ax.set_title(f"Residuals — {result.result.model_name}")
    ax.set_xlabel("Time")
    ax.set_ylabel("Actual - Predicted")


def _normalized_cdf(values: np.ndarray) -> np.ndarray:
    """Normalize a sequence to a CDF [0,1] with monotonic enforcement.

    - Clips negatives to 0
    - Enforces non-decreasing via cumulative maximum
    - Divides by the final total (last element) for time-consistent scaling
    """
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return arr
    arr = np.clip(arr, 0.0, None)
    arr = np.maximum.accumulate(arr)
    total = float(arr[-1])
    if total <= 0.0:
        return np.zeros_like(arr)
    return arr / total


def plot_u_plot(figure: Figure, dataset: FailureDataset, result: RankedModelResult) -> None:
    ax = figure.add_subplot(111)
    actual = _normalized_cdf(_actual_series(dataset))
    predicted = _normalized_cdf(_ensure_array(result.result.predictions))
    length = min(actual.size, predicted.size)
    ax.plot(predicted[:length], actual[:length], "o-", label=result.result.model_name)
    ax.plot([0, 1], [0, 1], linestyle="--", color="#666666", label="Ideal")
    ax.set_xlabel("Predicted CDF")
    ax.set_ylabel("Actual CDF")
    ax.set_title("U-Plot")
    ax.legend(loc="best")
    ax.grid(True, linestyle=":", alpha=0.4)


def plot_y_plot(figure: Figure, dataset: FailureDataset, result: RankedModelResult) -> None:
    ax = figure.add_subplot(111)
    actual = np.clip(_normalized_cdf(_actual_series(dataset)), 1e-6, 1 - 1e-6)
    predicted = np.clip(_normalized_cdf(_ensure_array(result.result.predictions)), 1e-6, 1 - 1e-6)
    length = min(actual.size, predicted.size)
    y_actual = -np.log(1.0 - actual[:length])
    y_pred = -np.log(1.0 - predicted[:length])
    ax.plot(y_pred, y_actual, "o-", label=result.result.model_name)
    ax.plot([y_pred.min(), y_pred.max()], [y_pred.min(), y_pred.max()], "--", color="#999999")
    ax.set_xlabel("Predicted Y")
    ax.set_ylabel("Actual Y")
    ax.set_title("Y-Plot")
    ax.legend(loc="best")
    ax.grid(True, linestyle=":", alpha=0.4)
