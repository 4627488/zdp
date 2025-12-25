"""Hybrid model combining EMD decomposition, SVR, and GM(1,1) smoothing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from scipy.signal import savgol_filter

from zdp.data import FailureDataset, FailureSeriesType

from .base import ModelResult, ReliabilityModel


@dataclass
class HybridConfig:
    svr_kernel: str = "rbf"
    svr_c: float = 20.0
    svr_epsilon: float = 0.01


class EMDHybridModel(ReliabilityModel):
    name = "EMD-SVR/GM Hybrid"
    required_series_type = FailureSeriesType.CUMULATIVE_FAILURES

    def __init__(self, config: HybridConfig | None = None) -> None:
        self.config = config or HybridConfig()
        self.param_count = 6
        self.components: List[dict[str, float]] = []

    def _fit(
        self,
        dataset: FailureDataset,
        *,
        evaluation_times: np.ndarray | None = None,
    ) -> ModelResult:
        time_axis = dataset.time_axis
        targets = dataset.cumulative_failures()
        imfs, residue = self._decompose_signal(targets)
        predictions = np.zeros_like(targets)
        component_info: List[dict[str, float]] = []
        for idx, imf in enumerate(imfs):
            component_pred = self._fit_component(time_axis, imf)
            predictions += component_pred
            component_info.append({"component": float(idx + 1), "variance": float(np.var(imf))})
        gm_pred = self._gm_predict(residue)
        blended = predictions + gm_pred
        eval_times = evaluation_times if evaluation_times is not None else time_axis
        metrics = self.compute_metrics(targets, blended)
        self.components = component_info
        diagnostics = {
            "components": component_info,
            "gm_variance": float(np.var(residue)),
        }
        return ModelResult(
            model_name=self.name,
            parameters={
                "svr_kernel": self.config.svr_kernel,
                "svr_c": self.config.svr_c,
                "svr_epsilon": self.config.svr_epsilon,
                "imfs": len(imfs),
            },
            times=eval_times,
            predictions=blended,
            metrics=metrics,
            diagnostics=diagnostics,
        )

    def _fit_component(self, time_axis: np.ndarray, component: np.ndarray) -> np.ndarray:
        pipeline = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "svr",
                    SVR(
                        kernel=self.config.svr_kernel,
                        C=self.config.svr_c,
                        epsilon=self.config.svr_epsilon,
                    ),
                ),
            ]
        )
        pipeline.fit(time_axis.reshape(-1, 1), component)
        return pipeline.predict(time_axis.reshape(-1, 1))

    @staticmethod
    def _gm_predict(series: np.ndarray) -> np.ndarray:
        x0 = np.asarray(series, dtype=float)
        if x0.size < 3:
            return series
        x1 = np.cumsum(x0)
        B = np.column_stack((-0.5 * (x1[:-1] + x1[1:]), np.ones(x0.size - 1)))
        Y = x0[1:]
        coeffs, *_ = np.linalg.lstsq(B, Y, rcond=None)
        a, b = coeffs
        x1_hat = [x0[0]]
        for k in range(1, x0.size):
            value = (x0[0] - b / a) * np.exp(-a * k) + b / a
            x1_hat.append(value)
        x1_hat = np.array(x1_hat)
        x0_hat = np.diff(x1_hat, prepend=x1_hat[0])
        return x0_hat

    def _decompose_signal(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        residual = values.copy()
        imfs: List[np.ndarray] = []
        max_components = min(3, max(1, values.size // 6))
        for _ in range(max_components):
            window = self._window_length(residual.size)
            if window is None:
                break
            smooth = savgol_filter(residual, window_length=window, polyorder=2, mode="interp")
            imf = residual - smooth
            if np.allclose(imf, 0, atol=1e-6):
                break
            imfs.append(imf)
            residual = smooth
        if not imfs:
            return np.zeros((0, values.size)), residual
        return np.vstack(imfs), residual

    @staticmethod
    def _window_length(size: int) -> int | None:
        if size < 7:
            return None
        length = size // 2
        if length % 2 == 0:
            length -= 1
        length = max(5, length)
        if length >= size:
            length = size - 2
            if length % 2 == 0:
                length -= 1
        return length if length >= 5 else None


__all__ = ["EMDHybridModel", "HybridConfig"]
