"""Experiment export/import helpers.

Exports a reproducible bundle containing:
- dataset (CSV)
- config (JSON)
- results summary (JSON)

This intentionally avoids pickling model objects.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from zdp.data import FailureDataset
from zdp.services.analysis import RankedModelResult


@dataclass(frozen=True)
class ExperimentConfig:
    """Minimal config snapshot for reproducibility."""

    created_at: str
    dataset_metadata: Mapping[str, Any]
    ranking_metric: str | None
    walk_forward: Mapping[str, Any]
    prediction_interval_alpha: float | None


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
        dataset_metadata=dict(dataset.metadata),
        ranking_metric=ranking_metric,
        walk_forward=dict(walk_forward or {}),
        prediction_interval_alpha=prediction_interval_alpha,
    )


def _dataset_to_csv(dataset: FailureDataset) -> str:
    # Keep it intentionally minimal and stable.
    lines = ["time,value"]
    for t, v in zip(dataset.time_axis.tolist(), dataset.values.tolist()):
        lines.append(f"{float(t)},{float(v)}")
    return "\n".join(lines) + "\n"


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


def _to_list(arr: np.ndarray) -> list[float]:
    return [float(x) for x in np.asarray(arr, dtype=float).tolist()]


__all__ = [
    "ExperimentConfig",
    "default_experiment_config",
    "export_experiment_zip",
]
