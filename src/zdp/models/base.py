"""Abstract base class for reliability growth models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
from scipy import stats

from zdp.data import FailureDataset, FailureSeriesType


@dataclass(frozen=True)
class ModelResult:
    """Container for the outcome of fitting a model to a dataset."""

    model_name: str
    parameters: Mapping[str, float | str]
    times: np.ndarray
    predictions: np.ndarray
    metrics: Mapping[str, float]
    diagnostics: Mapping[str, Any] | None = None


class ReliabilityModel(ABC):
    """Common behavior shared by all ZDP models."""

    name: str = "BaseModel"
    required_series_type: FailureSeriesType | None = None
    param_count: int = 2

    def supports(self, series_type: FailureSeriesType) -> bool:
        return self.required_series_type in (None, series_type)

    def fit(
        self,
        dataset: FailureDataset,
        *,
        evaluation_times: np.ndarray | None = None,
    ) -> ModelResult:
        self._validate_dataset(dataset)
        return self._fit(dataset, evaluation_times=evaluation_times)

    def _validate_dataset(self, dataset: FailureDataset) -> None:
        if self.required_series_type and dataset.series_type != self.required_series_type:
            raise ValueError(
                f"Model {self.name} expects '{self.required_series_type.value}' data, "
                f"received '{dataset.series_type.value}'."
            )

    @abstractmethod
    def _fit(
        self,
        dataset: FailureDataset,
        *,
        evaluation_times: np.ndarray | None = None,
    ) -> ModelResult:
        """Perform model-specific fitting logic."""

    def compute_metrics(
        self,
        actual: np.ndarray,
        predicted: np.ndarray,
        *,
        param_count: int | None = None,
    ) -> Mapping[str, float]:
        if actual.shape != predicted.shape:
            raise ValueError("Actual and predicted arrays must align")
        residuals = actual - predicted
        mse = float(np.mean(residuals**2))
        mae = float(np.mean(np.abs(residuals)))
        rmse = float(np.sqrt(mse))
        max_err = float(np.max(np.abs(residuals)))
        medae = float(np.median(np.abs(residuals)))
        safe_actual = np.clip(actual, 1e-8, None)
        mape = float(np.mean(np.abs(residuals / safe_actual)))
        ss_res = float(np.sum(residuals**2))
        ss_tot = float(np.sum((actual - actual.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        dof = actual.size
        param_count = param_count or self.param_count
        if dof > param_count and mse > 0:
            aic = float(dof * np.log(mse) + 2 * param_count)
            bic = float(dof * np.log(mse) + param_count * np.log(dof))
        else:
            aic = float("nan")
            bic = float("nan")
        chi2_obs = np.clip(actual, 1e-8, None)
        chi2_exp = np.clip(predicted, 1e-8, None)
        if np.any(chi2_exp):
            exp_sum = float(np.sum(chi2_exp))
            obs_sum = float(np.sum(chi2_obs))
            if exp_sum > 0 and not np.isclose(exp_sum, obs_sum):
                chi2_exp = chi2_exp * (obs_sum / exp_sum)
        try:
            chi2_stat, chi2_p = stats.chisquare(f_obs=chi2_obs, f_exp=chi2_exp)
        except ValueError:
            chi2_stat, chi2_p = float("nan"), float("nan")
        try:
            ks_stat, ks_p = stats.ks_2samp(actual, predicted)
        except ValueError:
            ks_stat, ks_p = float("nan"), float("nan")
        return {
            "mae": mae,
            "rmse": rmse,
            "mse": mse,
            "mape": mape,
            "max_error": max_err,
            "medae": medae,
            "r2": r2,
            "aic": aic,
            "bic": bic,
            "chi2": float(chi2_stat),
            "chi2_p": float(chi2_p),
            "ks": float(ks_stat),
            "ks_p": float(ks_p),
        }


__all__ = ["ModelResult", "ReliabilityModel"]
