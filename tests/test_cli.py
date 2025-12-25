import io
import numpy as np
import pandas as pd

from zdp.cli import run_cli


def test_cli_runs_go_model(tmp_path) -> None:
    time_axis = np.arange(1, 6)
    failures = np.array([1, 3, 6, 10, 15])
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
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 0
    output = stdout.getvalue()
    assert "Goel-Okumoto" in output
    assert "parameters" in output
    assert stderr.getvalue() == ""


def test_cli_returns_error_when_no_models_match(tmp_path) -> None:
    intervals = np.array([5.0, 4.0, 3.0])
    frame = pd.DataFrame({"interval": intervals})
    path = tmp_path / "tbf.csv"
    frame.to_csv(path, index=False)

    stdout = io.StringIO()
    stderr = io.StringIO()
    code = run_cli(
        [str(path), "--model", "go"],
        stdout=stdout,
        stderr=stderr,
    )

    assert code == 3
    assert "No compatible models" in stderr.getvalue()
    assert stdout.getvalue() == ""
