"""High-level orchestration helpers for running model suites."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

import numpy as np

from sras.data import FailureDataset
from sras.models import ModelResult, ReliabilityModel


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
    ) -> list[RankedModelResult]:
        results: list[ModelResult] = []
        for model in self._models:
            if not model.supports(dataset.series_type):
                continue
            results.append(model.fit(dataset, evaluation_times=evaluation_times))
        results.sort(key=lambda r: r.metrics.get("rmse", float("inf")))
        ranked = [RankedModelResult(rank=i + 1, result=res) for i, res in enumerate(results)]
        return ranked


__all__ = ["AnalysisService", "RankedModelResult"]
