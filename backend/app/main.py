from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error
from typing import List

from .schemas import PredictionRequest, PredictionResponse, AlgorithmResult, Metric, PreprocessRequest, PreprocessResponse
from .algorithms.go_model import GOModel
from .algorithms.jm_model import JMModel
from .algorithms.bp_model import BPModel
from .algorithms.new_models import StatisticalModel, BayesianModel
from .algorithms.llm_model import LLMModel
from .preprocessing import preprocess_data

app = FastAPI(title="Reliability Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALGORITHMS = {
    "GO": GOModel,
    "JM": JMModel,
    "BP": BPModel,
    "Statistical": StatisticalModel,
    "Bayesian": BayesianModel,
    "LLM": LLMModel
}


@app.post("/preprocess", response_model=PreprocessResponse)
async def preprocess_endpoint(request: PreprocessRequest):
    return preprocess_data(request.data, request.config)


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    tbf = np.array(request.tbf)
    n_total = len(tbf)
    n_train = int(n_total * request.train_ratio)

    if n_train < 5:
        raise HTTPException(status_code=400, detail="Not enough data for training")

    tbf_train = tbf[:n_train]
    tbf_test = tbf[n_train:]

    cumulative_time = np.cumsum(tbf)
    train_time = cumulative_time[:n_train]
    test_time_actual = cumulative_time[n_train:]

    last_train_time = train_time[-1]
    n_test = len(tbf_test)

    results = []

    for algo_name in request.algorithms:
        if algo_name not in ALGORITHMS:
            continue

        model_class = ALGORITHMS[algo_name]
        model = model_class()

        try:
            model.fit(tbf_train)
            predictions = model.predict(n_test, last_train_time)

            # Calculate metrics
            # Filter out NaNs for metric calculation
            valid_mask = ~np.isnan(predictions)
            if np.any(valid_mask):
                rmse = np.sqrt(
                    mean_squared_error(
                        test_time_actual[valid_mask], predictions[valid_mask]
                    )
                )
                mae = mean_absolute_error(
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

    return PredictionResponse(
        train_time=train_time.tolist(),
        test_time_actual=test_time_actual.tolist(),
        results=results,
    )


@app.get("/")
def read_root():
    return {"message": "Reliability Prediction API is running"}
