"""Dataset abstractions to keep raw failure data self-describing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

from .types import FailureSeriesType


@dataclass(frozen=True)
class FailureDataset:
    """Wraps a time series of failure measurements with minimal semantics."""

    time_axis: np.ndarray
    values: np.ndarray
    series_type: FailureSeriesType
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        time_axis = np.asarray(self.time_axis, dtype=float)
        values = np.asarray(self.values, dtype=float)
        if time_axis.shape != values.shape:
            if values.ndim != 1:
                raise ValueError("Values must be a 1-D array")
            if time_axis.ndim != 1:
                raise ValueError("Time axis must be a 1-D array")
            raise ValueError("Time and value arrays must share the same shape")
        if values.size == 0:
            raise ValueError("Failure dataset must not be empty")
        object.__setattr__(self, "time_axis", time_axis)
        object.__setattr__(self, "values", values)

    @property
    def size(self) -> int:
        return self.values.size

    def normalized(self, method: str = "min-max") -> "FailureDataset":
        """Return a new dataset with normalized value magnitudes."""

        method = method.lower()
        values = self.values
        if method == "min-max":
            span = values.max() - values.min()
            norm = (values - values.min()) / span if span > 0 else np.zeros_like(values)
        elif method == "z-score":
            std = values.std(ddof=0)
            norm = (values - values.mean()) / std if std > 0 else np.zeros_like(values)
        else:
            raise ValueError(f"Unsupported normalization method: {method}")
        return FailureDataset(
            time_axis=self.time_axis,
            values=norm,
            series_type=self.series_type,
            metadata=self.metadata,
        )

    def cumulative_failures(self) -> np.ndarray:
        """Return the cumulative failure count regardless of source representation."""

        if self.series_type == FailureSeriesType.CUMULATIVE_FAILURES:
            return self.values
        return np.cumsum(self.values)

    def failure_intervals(self) -> np.ndarray:
        """Return the failure intervals regardless of representation."""

        if self.series_type == FailureSeriesType.TIME_BETWEEN_FAILURES:
            return self.values
        return np.diff(np.insert(self.values, 0, 0.0))

    def detect_outliers(self, z_threshold: float = 3.0) -> np.ndarray:
        """Simple z-score based outlier detection mask."""

        values = self.values
        std = values.std(ddof=0)
        if std == 0:
            return np.zeros_like(values, dtype=bool)
        z_scores = (values - values.mean()) / std
        return np.abs(z_scores) > z_threshold

    def with_metadata(self, **extra: Any) -> "FailureDataset":
        """Return a copy with merged metadata entries."""

        new_meta = dict(self.metadata)
        new_meta.update(extra)
        return FailureDataset(
            time_axis=self.time_axis,
            values=self.values,
            series_type=self.series_type,
            metadata=new_meta,
        )

    def slice(self, stop: int) -> "FailureDataset":
        """Return a prefix of this dataset.

        Args:
            stop: Number of samples to keep from the start (like ``values[:stop]``).
        """

        if stop <= 0:
            raise ValueError("stop must be >= 1")
        return FailureDataset(
            time_axis=self.time_axis[:stop],
            values=self.values[:stop],
            series_type=self.series_type,
            metadata=self.metadata,
        )


__all__ = ["FailureDataset"]
