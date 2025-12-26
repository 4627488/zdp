import io

import numpy as np
import pandas as pd

from zdp.cli import run_cli
from zdp.data import FailureDataset, FailureSeriesType
from zdp.models import GoelOkumotoModel
from zdp.services import AnalysisService, WalkForwardConfig


def test_analysis_service_can_compute_cv_metrics_and_rank_by_cv(tmp_path) -> None:
    time_axis = np.arange(1, 16, dtype=float)
    a_true, b_true = 40.0, 0.08
    counts = a_true * (1.0 - np.exp(-b_true * time_axis))
    dataset = FailureDataset(time_axis=time_axis, values=counts, series_type=FailureSeriesType.CUMULATIVE_FAILURES)

    service = AnalysisService([GoelOkumotoModel()])
    ranked = service.run(
        dataset,
        validation=WalkForwardConfig(enabled=True, min_train_size=10, horizon=1),
        rank_by="cv_rmse",
    )

    assert ranked
    metrics = ranked[0].result.metrics
    assert "cv_rmse" in metrics
    assert metrics["cv_rmse"] >= 0


def test_cli_can_enable_walk_forward_and_prediction_interval(tmp_path) -> None:
    time_axis = np.arange(1, 10)
    failures = np.array([1, 2, 4, 7, 11, 16, 22, 29, 37])
    frame = pd.DataFrame({"time": time_axis, "failures": failures})
    path = tmp_path / "go.csv"
    frame.to_csv(path, index=False)

    stdout = io.StringIO()
    stderr = io.StringIO()
    code = run_cli(
        [
            str(path),
            "--time-column",
            "time",
            "--value-column",
            "failures",
            "--model",
            "go",
            "--walk-forward",
            "--cv-min-train",
            "6",
            "--prediction-interval-alpha",
            "0.05",
            "--rank-by",
            "cv_rmse",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 0
    out = stdout.getvalue()
    assert "CV_RMSE" in out
    assert stderr.getvalue() == ""


def test_cli_can_export_and_replay_experiment_zip(tmp_path) -> None:
    time_axis = np.arange(1, 10)
    failures = np.array([1, 2, 4, 7, 11, 16, 22, 29, 37])
    frame = pd.DataFrame({"time": time_axis, "failures": failures})
    data_path = tmp_path / "go.csv"
    frame.to_csv(data_path, index=False)

    zip_path = tmp_path / "exp.zip"

    stdout = io.StringIO()
    stderr = io.StringIO()
    code = run_cli(
        [
            str(data_path),
            "--time-column",
            "time",
            "--value-column",
            "failures",
            "--model",
            "go",
            "--walk-forward",
            "--cv-min-train",
            "6",
            "--rank-by",
            "cv_rmse",
            "--export-experiment",
            str(zip_path),
        ],
        stdout=stdout,
        stderr=stderr,
    )
    assert code == 0
    assert zip_path.exists()

    stdout2 = io.StringIO()
    stderr2 = io.StringIO()
    code2 = run_cli(
        [
            "--load-experiment",
            str(zip_path),
        ],
        stdout=stdout2,
        stderr=stderr2,
    )
    assert code2 == 0
    assert "CV_RMSE" in stdout2.getvalue()
    assert stderr2.getvalue() == ""
