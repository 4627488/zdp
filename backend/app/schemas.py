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
