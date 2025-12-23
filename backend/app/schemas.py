from pydantic import BaseModel
from typing import List, Optional, Dict


class PredictionRequest(BaseModel):
    tbf: List[float]
    train_ratio: float = 0.75  # Default 75% training
    algorithms: List[str] = ["GO", "JM", "BP"]


class Metric(BaseModel):
    rmse: Optional[float]
    mae: Optional[float]


class AlgorithmResult(BaseModel):
    name: str
    predicted_cumulative_time: List[Optional[float]]
    metrics: Metric


class PredictionResponse(BaseModel):
    train_time: List[float]
    test_time_actual: List[float]
    results: List[AlgorithmResult]


class PreprocessingConfig(BaseModel):
    handle_missing: bool = True
    missing_strategy: str = "mean"  # mean, median, drop
    detect_outliers: bool = True
    outlier_method: str = "zscore"  # zscore, iqr
    outlier_threshold: float = 3.0
    normalize: bool = False
    normalization_method: str = "minmax"  # minmax, zscore


class PreprocessRequest(BaseModel):
    data: List[float]
    config: PreprocessingConfig


class DistributionData(BaseModel):
    labels: List[float]
    counts: List[int]


class PreprocessResponse(BaseModel):
    original_data: List[float]
    processed_data: List[float]
    original_distribution: DistributionData
    processed_distribution: DistributionData
    stats: Dict[str, float]
