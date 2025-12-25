import numpy as np
import torch

from zdp.data import FailureDataset, FailureSeriesType
from zdp.models import (
    BPConfig,
    BPNeuralNetworkModel,
    EMDHybridModel,
    GoelOkumotoModel,
    HybridConfig,
    JelinskiMorandaModel,
    SShapedModel,
    SVRConfig,
    SupportVectorRegressionModel,
)


def test_goel_okumoto_fits_synthetic_data() -> None:
    time_axis = np.linspace(10, 100, num=10)
    a_true, b_true = 50.0, 0.05
    counts = a_true * (1.0 - np.exp(-b_true * time_axis))
    dataset = FailureDataset(
        time_axis=time_axis,
        values=counts,
        series_type=FailureSeriesType.CUMULATIVE_FAILURES,
    )

    model = GoelOkumotoModel()
    result = model.fit(dataset)

    assert abs(result.parameters["a"] - a_true) < 5.0
    assert abs(result.parameters["b"] - b_true) < 0.02
    assert result.metrics["rmse"] < 1e-2


def test_jelinski_moranda_predicts_positive_intervals() -> None:
    # Use an improving (in expectation) interval sequence so JM has a finite MLE solution.
    intervals = np.array([2.0, 3.0, 4.0, 5.0, 6.0])
    dataset = FailureDataset(
        time_axis=np.arange(1, intervals.size + 1),
        values=intervals,
        series_type=FailureSeriesType.TIME_BETWEEN_FAILURES,
    )

    model = JelinskiMorandaModel()
    result = model.fit(dataset)

    assert result.parameters["N0"] > intervals.size
    assert 0 < result.parameters["phi"] < 1.0
    assert np.all(result.predictions > 0)


def test_s_shaped_model_tracks_s_curve() -> None:
    time_axis = np.linspace(1, 40, num=20)
    a_true, b_true = 80.0, 0.08
    counts = a_true * (1.0 - (1.0 + b_true * time_axis) * np.exp(-b_true * time_axis))
    dataset = FailureDataset(time_axis=time_axis, values=counts, series_type=FailureSeriesType.CUMULATIVE_FAILURES)

    model = SShapedModel()
    result = model.fit(dataset)

    assert abs(result.parameters["a"] - a_true) < 10
    assert result.metrics["rmse"] < 1.0


def test_svr_model_follows_quadratic_series() -> None:
    time_axis = np.linspace(0, 5, num=30)
    counts = 3 * time_axis**2 + 2
    dataset = FailureDataset(time_axis=time_axis, values=counts, series_type=FailureSeriesType.CUMULATIVE_FAILURES)

    model = SupportVectorRegressionModel(
        SVRConfig(kernel="rbf", c=200.0, epsilon=0.001, gamma="auto")
    )
    result = model.fit(dataset)

    assert result.metrics["rmse"] < 0.4


def test_bp_neural_network_model_learns_linear_series() -> None:
    torch.manual_seed(1)
    time_axis = np.linspace(0, 1, num=32)
    counts = 15 * time_axis + 5
    dataset = FailureDataset(time_axis=time_axis, values=counts, series_type=FailureSeriesType.CUMULATIVE_FAILURES)

    config = BPConfig(hidden_size=6, epochs=600, learning_rate=0.08, momentum=0.7, train_split=0.85)
    model = BPNeuralNetworkModel(config)
    result = model.fit(dataset)

    assert result.metrics["rmse"] < 0.5


def test_emd_hybrid_model_outputs_prediction() -> None:
    time_axis = np.linspace(0, 10, num=40)
    counts = 10 + 2 * np.sin(time_axis) + 0.3 * time_axis
    dataset = FailureDataset(time_axis=time_axis, values=counts, series_type=FailureSeriesType.CUMULATIVE_FAILURES)

    model = EMDHybridModel(HybridConfig(svr_kernel="rbf", svr_c=10.0, svr_epsilon=0.01))
    result = model.fit(dataset)

    assert result.predictions.shape == counts.shape
    assert result.metrics["rmse"] < 2.0
