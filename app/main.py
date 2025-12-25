from typing import Any, Dict, List, Type
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error

from .schemas import (
    PredictionRequest,
    PredictionResponse,
    AlgorithmResult,
    Metric,
    PreprocessRequest,
    PreprocessResponse,
    AnalysisInsights,
)
from .algorithms.go_model import GOModel
from .algorithms.jm_model import JMModel
from .algorithms.bp_model import BPModel
from .algorithms.new_models import StatisticalModel, BayesianModel
from .algorithms.llm_model import LLMModel
from .algorithms.base import ReliabilityModel
from .preprocessing import preprocess_data
from .analysis import ReliabilityAnalysis

app: FastAPI = FastAPI(title="Reliability Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALGORITHMS: Dict[str, Type[ReliabilityModel]] = {
    "GO": GOModel,
    "JM": JMModel,
    "BP": BPModel,
    "Statistical": StatisticalModel,
    "Bayesian": BayesianModel,
    "LLM": LLMModel
}


@app.post("/preprocess", response_model=PreprocessResponse)
async def preprocess_endpoint(request: PreprocessRequest) -> PreprocessResponse:
    """Preprocess reliability data.

    Args:
        request: PreprocessRequest with data and configuration.

    Returns:
        PreprocessResponse with processed data and statistics.
    """
    return preprocess_data(request.data, request.config)


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest) -> PredictionResponse:
    """Predict reliability using multiple algorithms.

    Args:
        request: PredictionRequest with TBF data and algorithm selection.

    Returns:
        PredictionResponse with predictions and analysis.

    Raises:
        HTTPException: If not enough data for training.
    """
    tbf: np.ndarray = np.array(request.tbf)
    n_total: int = len(tbf)
    n_train: int = int(n_total * request.train_ratio)

    if n_train < 5:
        raise HTTPException(status_code=400, detail="Not enough data for training")

    tbf_train: np.ndarray = tbf[:n_train]
    tbf_test: np.ndarray = tbf[n_train:]

    cumulative_time: np.ndarray = np.cumsum(tbf)
    train_time: np.ndarray = cumulative_time[:n_train]
    test_time_actual: np.ndarray = cumulative_time[n_train:]

    last_train_time: np.floating[Any] = train_time[-1]
    n_test: int = len(tbf_test)

    results: List[AlgorithmResult] = []

    for algo_name in request.algorithms:
        if algo_name not in ALGORITHMS:
            continue

        model_class: Type[ReliabilityModel] = ALGORITHMS[algo_name]
        model: ReliabilityModel = model_class()

        try:
            model.fit(tbf_train)
            predictions: np.ndarray = model.predict(n_test, last_train_time)

            # Calculate metrics
            # Filter out NaNs for metric calculation
            valid_mask: np.ndarray = ~np.isnan(predictions)
            if np.any(valid_mask):
                rmse: float = np.sqrt(
                    mean_squared_error(
                        test_time_actual[valid_mask], predictions[valid_mask]
                    )
                )
                mae: float = mean_absolute_error(
                    test_time_actual[valid_mask], predictions[valid_mask]
                )
            else:
                rmse = None
                mae = None

            results.append(
                AlgorithmResult(
                    name=model.name,
                    predicted_cumulative_time=[
                        float(x) if not np.isnan(x) else None for x in predictions
                    ],
                    metrics=Metric(rmse=rmse, mae=mae),
                )
            )

        except Exception as e:
            print(f"Error in {algo_name}: {e}")
            results.append(
                AlgorithmResult(
                    name=model.name,
                    predicted_cumulative_time=[None] * n_test,
                    metrics=Metric(rmse=None, mae=None),
                )
            )

    analysis: Dict[str, Any] = ReliabilityAnalysis(
        tbf, train_time, results
    ).analyze(include_llm=False)

    return PredictionResponse(
        train_time=train_time.tolist(),
        test_time_actual=test_time_actual.tolist(),
        results=results,
        analysis=AnalysisInsights(**analysis)
    )


@app.post("/analyze/llm")
async def generate_llm_report(analysis: AnalysisInsights) -> Dict[str, str]:
    """Generate LLM-assisted reliability report.

    Args:
        analysis: AnalysisInsights object with analysis data.

    Returns:
        Dictionary with 'report' key containing the generated report.
    """
    # Create a dummy instance just to access the method and client
    analyzer: ReliabilityAnalysis = ReliabilityAnalysis([], [], [])

    stats: Dict[str, Any] = {
        "total_failures": analysis.total_failures,
        "total_time": analysis.total_time,
        "laplace_factor": analysis.laplace_factor,
        "trend_assessment": analysis.trend_assessment,
        "best_model": analysis.best_model,
        "best_rmse": analysis.best_rmse,
        "failure_intensity": analysis.failure_intensity
    }

    report: str = analyzer.generate_deepseek_report(stats)
    return {"report": report}


@app.get("/")
def read_root() -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        Dictionary with status message.
    """
    return {"message": "Reliability Prediction API is running"}
