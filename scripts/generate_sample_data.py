"""Generate synthetic reliability datasets for ZDP demos."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "samples"
DEST.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(20251225)


def _write_csv(name: str, frame: pd.DataFrame) -> Path:
    path = DEST / name
    frame.to_csv(path, index=False)
    return path


def build_goel_okumoto_sample() -> Path:
    """Smooth cumulative series representative of NHPP (GO) behavior."""

    time = np.linspace(10, 320, 30)
    a, b = 130.0, 0.035
    expected = a * (1.0 - np.exp(-b * time))
    noise = RNG.normal(0.0, 1.8, size=time.size)
    failures = np.maximum.accumulate(np.round(expected + noise).clip(0))
    frame = pd.DataFrame(
        {
            "time": np.round(time, 1),
            "failures": failures.astype(int),
        }
    )
    return _write_csv("nhpp_goel_okumoto.csv", frame)


def build_s_shaped_tbf_sample() -> Path:
    """Time-between-failure intervals derived from a logistic release curve."""

    cycles = np.arange(1, 45)
    total = 95.0
    k, midpoint = 0.22, 20.0
    logistic = total / (1.0 + np.exp(-k * (cycles - midpoint)))
    deltas = np.diff(np.insert(logistic, 0, 0.0))
    tbfs = np.clip(deltas + RNG.normal(0.0, 0.3, size=deltas.size), 0.15, None)
    frame = pd.DataFrame({"cycle": cycles, "tbf": np.round(tbfs, 3)})
    return _write_csv("tbf_s_shaped.csv", frame)


def build_field_weekly_counts_sample() -> Path:
    """Piecewise cumulative failures emulating phased field testing."""

    weeks = np.arange(1, 33)
    base_rates = np.piecewise(
        weeks,
        [weeks <= 10, (weeks > 10) & (weeks <= 20), weeks > 20],
        [lambda w: 3.5 * w, lambda w: 35 + 2.2 * (w - 10), lambda w: 57 + 1.2 * (w - 20)],
    )
    fluctuations = RNG.normal(0.0, 1.0, size=weeks.size)
    cumulative = np.maximum.accumulate(np.round(base_rates + fluctuations).clip(0))
    frame = pd.DataFrame(
        {
            "week": weeks,
            "cumulative": cumulative.astype(int),
        }
    )
    return _write_csv("field_weekly_counts.csv", frame)


def main() -> None:
    generators = [
        ("NHPP GO", build_goel_okumoto_sample),
        ("S-shaped TBF", build_s_shaped_tbf_sample),
        ("Field weekly", build_field_weekly_counts_sample),
    ]
    for label, builder in generators:
        path = builder()
        print(f"Wrote {label}: {path}")


if __name__ == "__main__":
    main()
