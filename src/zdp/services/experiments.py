"""Experiment export/import helpers.

Exports a reproducible bundle containing:
- dataset (CSV)
- config (JSON)
- results summary (JSON)

This intentionally avoids pickling model objects.
"""

from __future__ import annotations

import json
import csv
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from zdp.data import FailureDataset, FailureSeriesType
from zdp.models import ModelResult
from zdp.services.analysis import RankedModelResult


@dataclass(frozen=True)
class ExperimentConfig:
    """Minimal config snapshot for reproducibility."""

    created_at: str
    series_type: str
    dataset_metadata: Mapping[str, Any]
    ranking_metric: str | None
    walk_forward: Mapping[str, Any]
    prediction_interval_alpha: float | None


@dataclass(frozen=True)
class LoadedExperiment:
    dataset: FailureDataset
    ranked_results: list[RankedModelResult]
    config: ExperimentConfig


def export_experiment_zip(
    dataset: FailureDataset,
    ranked_results: Sequence[RankedModelResult],
    *,
    output_path: str | Path,
    config: ExperimentConfig,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dataset_csv = _dataset_to_csv(dataset)
    results_json = _results_to_json(ranked_results)
    config_json = json.dumps(asdict(config), ensure_ascii=False, indent=2)

    with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dataset.csv", dataset_csv)
        zf.writestr("config.json", config_json)
        zf.writestr("results.json", results_json)

    return output_path


def default_experiment_config(
    dataset: FailureDataset,
    *,
    ranking_metric: str | None,
    walk_forward: Mapping[str, Any] | None,
    prediction_interval_alpha: float | None,
) -> ExperimentConfig:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return ExperimentConfig(
        created_at=created_at,
        series_type=str(dataset.series_type.value),
        dataset_metadata=dict(dataset.metadata),
        ranking_metric=ranking_metric,
        walk_forward=dict(walk_forward or {}),
        prediction_interval_alpha=prediction_interval_alpha,
    )


def load_experiment_zip(path: str | Path) -> LoadedExperiment:
    """Load an experiment bundle and reconstruct dataset + ranked results."""

    path = Path(path)
    with zipfile.ZipFile(path, mode="r") as zf:
        dataset_csv = zf.read("dataset.csv").decode("utf-8")
        config_json = zf.read("config.json").decode("utf-8")
        results_json = zf.read("results.json").decode("utf-8")

    raw_cfg = json.loads(config_json)
    series_type_value = raw_cfg.get("series_type")
    if not series_type_value:
        # Backward-compatible: infer from value monotonicity.
        series_type_value = None

    dataset = _dataset_from_csv(dataset_csv, series_type_value=series_type_value)
    cfg = ExperimentConfig(
        created_at=str(raw_cfg.get("created_at", "")),
        series_type=str(series_type_value or dataset.series_type.value),
        dataset_metadata=dict(raw_cfg.get("dataset_metadata") or {}),
        ranking_metric=raw_cfg.get("ranking_metric"),
        walk_forward=dict(raw_cfg.get("walk_forward") or {}),
        prediction_interval_alpha=raw_cfg.get("prediction_interval_alpha"),
    )
    ranked = _results_from_json(results_json)
    return LoadedExperiment(dataset=dataset, ranked_results=ranked, config=cfg)


def _dataset_to_csv(dataset: FailureDataset) -> str:
    # Keep it intentionally minimal and stable.
    lines = ["time,value"]
    for t, v in zip(dataset.time_axis.tolist(), dataset.values.tolist()):
        lines.append(f"{float(t)},{float(v)}")
    return "\n".join(lines) + "\n"


def _dataset_from_csv(payload: str, *, series_type_value: str | None) -> FailureDataset:
    reader = csv.DictReader(StringIO(payload))
    times: list[float] = []
    values: list[float] = []
    for row in reader:
        times.append(float(row["time"]))
        values.append(float(row["value"]))

    time_axis = np.asarray(times, dtype=float)
    vals = np.asarray(values, dtype=float)

    if series_type_value:
        series_type = FailureSeriesType.from_string(series_type_value)
    else:
        diffs = np.diff(vals)
        series_type = (
            FailureSeriesType.CUMULATIVE_FAILURES
            if diffs.size > 0 and np.all(diffs >= 0)
            else FailureSeriesType.TIME_BETWEEN_FAILURES
        )

    return FailureDataset(time_axis=time_axis, values=vals, series_type=series_type)


def _results_to_json(ranked_results: Sequence[RankedModelResult]) -> str:
    payload: list[dict[str, Any]] = []
    for ranked in ranked_results:
        res = ranked.result
        payload.append(
            {
                "rank": ranked.rank,
                "model_name": res.model_name,
                "parameters": dict(res.parameters),
                "metrics": dict(res.metrics),
                "times": _to_list(res.times),
                "predictions": _to_list(res.predictions),
                "diagnostics": res.diagnostics,
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _results_from_json(payload: str) -> list[RankedModelResult]:
    raw = json.loads(payload)
    ranked: list[RankedModelResult] = []
    for entry in raw:
        result = ModelResult(
            model_name=str(entry.get("model_name")),
            parameters=dict(entry.get("parameters") or {}),
            times=np.asarray(entry.get("times") or [], dtype=float),
            predictions=np.asarray(entry.get("predictions") or [], dtype=float),
            metrics=dict(entry.get("metrics") or {}),
            diagnostics=entry.get("diagnostics"),
        )
        ranked.append(RankedModelResult(rank=int(entry.get("rank", 0)), result=result))
    ranked.sort(key=lambda r: r.rank)
    return ranked


def _to_list(arr: np.ndarray) -> list[float]:
    return [float(x) for x in np.asarray(arr, dtype=float).tolist()]


__all__ = [
    "ExperimentConfig",
    "LoadedExperiment",
    "default_experiment_config",
    "export_experiment_zip",
    "load_experiment_zip",
]
