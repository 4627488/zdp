"""High-level orchestration helpers for running model suites."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

import numpy as np

from zdp.data import FailureDataset, FailureSeriesType
from zdp.models import ModelResult, ReliabilityModel

from .intervals import normal_prediction_interval
from .validation import WalkForwardConfig, walk_forward_validate


@dataclass
class RankedModelResult:
    """Wraps a ModelResult with its rank for convenient UI/CLI use."""

    rank: int
    result: ModelResult


class AnalysisService:
    """Run a collection of models against a dataset and rank the outcomes."""

    def __init__(self, models: Iterable[ReliabilityModel] | None = None) -> None:
        self._models: List[ReliabilityModel] = list(models or [])

    def register(self, *models: ReliabilityModel) -> None:
        self._models.extend(models)

    @property
    def models(self) -> Sequence[ReliabilityModel]:
        return tuple(self._models)

    def run(
        self,
        dataset: FailureDataset,
        *,
        evaluation_times: np.ndarray | None = None,
        validation: WalkForwardConfig | None = None,
        rank_by: str | None = None,
        prediction_interval_alpha: float | None = None,
    ) -> list[RankedModelResult]:
        results: list[ModelResult] = []
        validation = validation or WalkForwardConfig(enabled=False)
        for model in self._models:
            if not model.supports(dataset.series_type):
                continue
            try:
                base = model.fit(dataset, evaluation_times=evaluation_times)
                diagnostics: dict[str, object] = dict(base.diagnostics or {})

                if validation.enabled:
                    cv_metrics, cv_diag = walk_forward_validate(model, dataset, validation)
                    diagnostics.update(cv_diag)
                else:
                    cv_metrics = {}

                if prediction_interval_alpha is not None:
                    # Compute interval on in-sample alignment to the dataset.
                    actual = (
                        dataset.cumulative_failures()
                        if dataset.series_type == FailureSeriesType.CUMULATIVE_FAILURES
                        else dataset.failure_intervals()
                    )
                    predicted = np.asarray(base.predictions, dtype=float)
                    length = int(min(actual.size, predicted.size))
                    if length >= 2:
                        lower, upper, pi_diag = normal_prediction_interval(
                            actual[:length], predicted[:length], alpha=prediction_interval_alpha
                        )
                        diagnostics["prediction_interval"] = {
                            "lower": lower,
                            "upper": upper,
                            **pi_diag,
                        }

                merged_metrics = dict(base.metrics)
                merged_metrics.update(cv_metrics)
                results.append(
                    ModelResult(
                        model_name=base.model_name,
                        parameters=base.parameters,
                        times=base.times,
                        predictions=base.predictions,
                        metrics=merged_metrics,
                        diagnostics=diagnostics or None,
                    )
                )
            except Exception:
                # Skip models that cannot be fitted for the given dataset.
                continue

        metric = (rank_by or ("cv_rmse" if validation.enabled else "rmse")).lower()
        reverse = metric in {"r2", "cv_r2"}

        def _score(res: ModelResult) -> float:
            value = res.metrics.get(metric)
            if value is None:
                value = res.metrics.get("rmse", float("inf"))
            return float(value)

        results.sort(key=_score, reverse=reverse)
        ranked = [RankedModelResult(rank=i + 1, result=res) for i, res in enumerate(results)]
        return ranked


__all__ = ["AnalysisService", "RankedModelResult", "WalkForwardConfig"]
