"""Type helpers describing failure data semantics."""

from __future__ import annotations

from enum import Enum


class FailureSeriesType(str, Enum):
    """Enumerates the supported time series representations for failure records."""

    TIME_BETWEEN_FAILURES = "time_between_failures"
    CUMULATIVE_FAILURES = "cumulative_failures"

    @classmethod
    def from_string(cls, raw: str | "FailureSeriesType") -> "FailureSeriesType":
        """Attempt to coerce an arbitrary string into a known enum member."""

        if isinstance(raw, FailureSeriesType):
            return raw
        normalized = raw.strip().lower()
        mapping = {
            "tbf": cls.TIME_BETWEEN_FAILURES,
            "time-between-failures": cls.TIME_BETWEEN_FAILURES,
            "interval": cls.TIME_BETWEEN_FAILURES,
            "cumulative": cls.CUMULATIVE_FAILURES,
            "cum": cls.CUMULATIVE_FAILURES,
            "failures": cls.CUMULATIVE_FAILURES,
        }
        return mapping.get(normalized, cls.TIME_BETWEEN_FAILURES)


__all__ = ["FailureSeriesType"]
