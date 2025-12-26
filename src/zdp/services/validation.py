"""Validation helpers (e.g., walk-forward evaluation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from zdp.data import FailureDataset, FailureSeriesType
from zdp.models import ReliabilityModel


@dataclass(frozen=True)
class WalkForwardConfig:
    """Configuration for expanding-window walk-forward validation."""

    enabled: bool = True
    min_train_size: int | None = None
    horizon: int = 1


def _actual_series(dataset: FailureDataset) -> np.ndarray:
    if dataset.series_type == FailureSeriesType.CUMULATIVE_FAILURES:
        return dataset.cumulative_failures()
    return dataset.failure_intervals()


def walk_forward_validate(
    model: ReliabilityModel,
    dataset: FailureDataset,
    config: WalkForwardConfig,
) -> tuple[Mapping[str, float], Mapping[str, Any]]:
    """Run walk-forward validation.

    Returns:
        (metrics, diagnostics)

    Notes:
        - Uses an expanding training window.
        - Computes metrics on the concatenated validation targets/predictions.
        - If the model cannot produce required-length predictions for a split, that split is skipped.
    """

    if not config.enabled:
        return {}, {}

    horizon = int(config.horizon)
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    actual = _actual_series(dataset)
    n_total = int(actual.size)

    if n_total <= horizon + 1:
        raise ValueError("Dataset too small for walk-forward validation")

    default_min = max(3, int(np.ceil(0.6 * n_total)))
    min_train = int(config.min_train_size or default_min)
    min_train = max(2, min(min_train, n_total - horizon))

    y_true_parts: list[np.ndarray] = []
    y_pred_parts: list[np.ndarray] = []
    attempted = 0
    used = 0

    for train_stop in range(min_train, n_total - horizon + 1):
        attempted += 1
        train_dataset = dataset.slice(train_stop)
        eval_stop = train_stop + horizon
        eval_times = dataset.time_axis[:eval_stop]

        try:
            res = model.clone().fit(train_dataset, evaluation_times=eval_times)
        except Exception:
            continue

        preds = np.asarray(res.predictions, dtype=float)
        if preds.size < eval_stop:
            continue

        y_true = actual[train_stop:eval_stop]
        y_pred = preds[train_stop:eval_stop]
        if y_true.shape != y_pred.shape:
            continue

        y_true_parts.append(y_true)
        y_pred_parts.append(y_pred)
        used += 1

    if used == 0:
        return {}, {"cv_attempted": attempted, "cv_used": 0}

    y_true_all = np.concatenate(y_true_parts)
    y_pred_all = np.concatenate(y_pred_parts)
    metrics = model.compute_metrics(y_true_all, y_pred_all)

    prefixed = {f"cv_{k}": float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
    diagnostics: dict[str, Any] = {
        "cv_attempted": attempted,
        "cv_used": used,
        "cv_min_train": min_train,
        "cv_horizon": horizon,
        "cv_points": int(y_true_all.size),
    }
    return prefixed, diagnostics


__all__ = ["WalkForwardConfig", "walk_forward_validate"]
