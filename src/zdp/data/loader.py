"""File loading helpers for reliability datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

from .dataset import FailureDataset
from .types import FailureSeriesType


class DataFormatError(ValueError):
    """Raised when an input table cannot be interpreted as a failure dataset."""


_TIME_CANDIDATES = {"time", "t", "timestamp", "elapsed", "duration"}
_TBF_VALUE_CANDIDATES = {
    "tbf",
    "interval",
    "delta",
    "interfailure",
    "tbfs",
    "dt",
}
_CUM_VALUE_CANDIDATES = {
    "cumulative",
    "failures",
    "failure",
    "count",
    "n",
    "nt",
    "mt",
}
SUPPORTED_EXTENSIONS = {".csv", ".txt", ".tsv", ".xls", ".xlsx"}


def load_failure_dataframe(path: str | Path, **read_kwargs: Mapping[str, object]) -> pd.DataFrame:
    """Load a raw dataframe from CSV/Excel based on file extension."""

    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise DataFormatError(f"Unsupported file extension: {suffix}")
    if suffix in {".xls", ".xlsx"}:
        frame = pd.read_excel(path, **read_kwargs)
    else:
        csv_kwargs = dict(read_kwargs)
        if suffix == ".tsv":
            csv_kwargs.setdefault("sep", "\t")
        frame = pd.read_csv(path, **csv_kwargs)
    if frame.empty:
        raise DataFormatError("Input file contains no rows")
    return frame


def load_failure_data(
    path: str | Path,
    *,
    series_type: FailureSeriesType | None = None,
    time_column: str | None = None,
    value_column: str | None = None,
    read_kwargs: Mapping[str, object] | None = None,
) -> FailureDataset:
    """Load a failure dataset from disk with lightweight column inference."""

    read_kwargs = dict(read_kwargs or {})
    frame = load_failure_dataframe(path, **read_kwargs)
    resolved_value = _resolve_value_column(frame, value_column)
    resolved_time = _resolve_time_column(frame, time_column, exclude=resolved_value)

    values = frame[resolved_value].to_numpy(dtype=float)
    time_axis = (
        frame[resolved_time].to_numpy(dtype=float)
        if resolved_time is not None
        else np.arange(1, values.size + 1, dtype=float)
    )

    # Prefer explicit series_type; else infer from column name, finally fallback to value monotonicity
    if series_type is not None:
        inferred_type = series_type
    else:
        col_lower = resolved_value.lower().strip()
        if col_lower in _TBF_VALUE_CANDIDATES:
            inferred_type = FailureSeriesType.TIME_BETWEEN_FAILURES
        elif col_lower in _CUM_VALUE_CANDIDATES:
            inferred_type = FailureSeriesType.CUMULATIVE_FAILURES
        else:
            inferred_type = _infer_series_type(values)
    dataset = FailureDataset(
        time_axis=time_axis,
        values=values,
        series_type=inferred_type,
        metadata={"path": str(path), "columns": list(frame.columns)},
    )
    return dataset


def _resolve_time_column(frame: pd.DataFrame, explicit: str | None, *, exclude: str) -> str | None:
    if explicit:
        if explicit not in frame.columns:
            raise DataFormatError(f"Time column '{explicit}' not present in file")
        return explicit
    lowercase_map = {col.lower().strip(): col for col in frame.columns if col != exclude}
    for candidate in _TIME_CANDIDATES:
        if candidate in lowercase_map:
            return lowercase_map[candidate]
    return None


def _resolve_value_column(frame: pd.DataFrame, explicit: str | None) -> str:
    if explicit:
        if explicit not in frame.columns:
            raise DataFormatError(f"Value column '{explicit}' not present in file")
        return explicit
    numeric_columns = [col for col in frame.columns if pd.api.types.is_numeric_dtype(frame[col])]
    if not numeric_columns:
        raise DataFormatError("No numeric columns detected for failure values")
    lowercase_map = {col.lower().strip(): col for col in numeric_columns}
    for candidate in (*_TBF_VALUE_CANDIDATES, *_CUM_VALUE_CANDIDATES):
        if candidate in lowercase_map:
            return lowercase_map[candidate]
    if len(numeric_columns) == 1:
        return numeric_columns[0]
    return numeric_columns[0]


def _infer_series_type(values: np.ndarray) -> FailureSeriesType:
    if values.ndim != 1:
        raise DataFormatError("Failure values must be a 1-D array")
    diffs = np.diff(values)
    if np.all(diffs >= 0):
        return FailureSeriesType.CUMULATIVE_FAILURES
    return FailureSeriesType.TIME_BETWEEN_FAILURES


__all__ = ["FailureDataset", "FailureSeriesType", "load_failure_data", "load_failure_dataframe"]
