import numpy as np
import pandas as pd

from sras.data import FailureSeriesType, load_failure_data


def test_load_time_between_failure_csv(tmp_path) -> None:
    raw = pd.DataFrame({"interval": [5, 4, 3, 2]})
    path = tmp_path / "tbf.csv"
    raw.to_csv(path, index=False)

    dataset = load_failure_data(path)

    assert dataset.series_type == FailureSeriesType.TIME_BETWEEN_FAILURES
    assert np.allclose(dataset.values, [5, 4, 3, 2])
    assert np.allclose(dataset.cumulative_failures(), [5, 9, 12, 14])


def test_load_cumulative_csv_with_explicit_columns(tmp_path) -> None:
    time = np.arange(1, 6) * 10
    counts = np.array([2, 5, 9, 14, 20])
    raw = pd.DataFrame({"time": time, "failures": counts})
    path = tmp_path / "cum.csv"
    raw.to_csv(path, index=False)

    dataset = load_failure_data(
        path,
        time_column="time",
        value_column="failures",
        series_type=FailureSeriesType.CUMULATIVE_FAILURES,
    )

    assert dataset.series_type == FailureSeriesType.CUMULATIVE_FAILURES
    assert np.allclose(dataset.time_axis, time)
    assert np.allclose(dataset.values, counts)
    assert np.allclose(dataset.failure_intervals(), np.diff(np.insert(counts, 0, 0)))
