"""Command-line interface for ZDP analyses."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence, TextIO

import numpy as np

from .data import FailureSeriesType, load_failure_data
from .models import (
    BPConfig,
    BPNeuralNetworkModel,
    EMDHybridModel,
    GoelOkumotoModel,
    HybridConfig,
    JelinskiMorandaModel,
    ReliabilityModel,
    SShapedModel,
    SVRConfig,
    SupportVectorRegressionModel,
    GM11Model,
    load_plugin_model_factories,
)
from .reporting import ReportBuilder
from .services import AnalysisService, WalkForwardConfig
from .services.experiments import default_experiment_config, export_experiment_zip
from .services import load_experiment_zip

ModelFactory = Callable[[], ReliabilityModel]


def _build_model_registry(args: argparse.Namespace) -> Mapping[str, tuple[str, ModelFactory]]:
    bp_config = BPConfig(
        hidden_size=args.bp_hidden,
        epochs=args.bp_epochs,
        learning_rate=args.bp_lr,
        momentum=args.bp_momentum,
        train_split=args.bp_split,
    )
    svr_config = SVRConfig(
        kernel=args.svr_kernel,
        c=args.svr_c,
        epsilon=args.svr_epsilon,
    )
    hybrid_config = HybridConfig(
        svr_kernel=args.svr_kernel,
        svr_c=args.hybrid_svr_c,
        svr_epsilon=args.hybrid_svr_epsilon,
    )
    return {
        "jm": (JelinskiMorandaModel.name, JelinskiMorandaModel),
        "jelinski-moranda": (JelinskiMorandaModel.name, JelinskiMorandaModel),
        "go": (GoelOkumotoModel.name, GoelOkumotoModel),
        "goel-okumoto": (GoelOkumotoModel.name, GoelOkumotoModel),
        "gm": (GM11Model.name, GM11Model),
        "s-shaped": (SShapedModel.name, SShapedModel),
        "s": (SShapedModel.name, SShapedModel),
        "bp": (BPNeuralNetworkModel.name, lambda: BPNeuralNetworkModel(bp_config)),
        "svr": (SupportVectorRegressionModel.name, lambda: SupportVectorRegressionModel(svr_config)),
        "hybrid": (EMDHybridModel.name, lambda: EMDHybridModel(hybrid_config)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zdp-cli",
        description="Run reliability models against a dataset and view ranked metrics.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to the CSV/Excel dataset containing failure data.",
    )
    parser.add_argument(
        "--load-experiment",
        default="",
        help="Replay a previously exported experiment zip (prints rankings / optional report).",
    )
    parser.add_argument(
        "--series-type",
        choices=[member.value for member in FailureSeriesType],
        help="Hint the data representation when auto-inference is insufficient.",
    )
    parser.add_argument("--time-column", help="Name of the column containing time values.")
    parser.add_argument("--value-column", help="Name of the column containing failure values.")
    parser.add_argument(
        "--model",
        dest="models",
        action="append",
        metavar="NAME",
        help="Specify one or more model identifiers (jm, go). Defaults to all supported models.",
    )
    parser.add_argument("--report", help="Optional path to save a PDF analysis report.")

    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="Enable expanding-window walk-forward validation (adds cv_* metrics).",
    )
    parser.add_argument(
        "--cv-min-train",
        type=int,
        default=0,
        help="Minimum training size for walk-forward (0=auto).",
    )
    parser.add_argument(
        "--cv-horizon",
        type=int,
        default=1,
        help="Forecast horizon per split for walk-forward validation.",
    )
    parser.add_argument(
        "--rank-by",
        default="",
        help="Metric key to rank models by (e.g., rmse, cv_rmse, r2).",
    )
    parser.add_argument(
        "--prediction-interval-alpha",
        type=float,
        default=-1.0,
        help="If set (e.g., 0.05), compute a simple prediction interval band.",
    )
    parser.add_argument(
        "--include-plugins",
        action="store_true",
        help="Also load models from Python entry points group 'zdp.models'.",
    )
    parser.add_argument(
        "--export-experiment",
        default="",
        help="Export a reproducible experiment bundle zip (dataset.csv/config.json/results.json).",
    )

    parser.add_argument("--bp-hidden", type=int, default=16, help="Hidden nodes for BP model.")
    parser.add_argument("--bp-epochs", type=int, default=800, help="Epochs for BP model training.")
    parser.add_argument("--bp-lr", type=float, default=0.01, help="Learning rate for BP model.")
    parser.add_argument("--bp-momentum", type=float, default=0.9, help="Momentum for BP model.")
    parser.add_argument(
        "--bp-split",
        type=float,
        default=0.8,
        help="Train split ratio for BP model (0-1).",
    )
    parser.add_argument(
        "--svr-kernel",
        choices=["rbf", "poly", "linear", "sigmoid"],
        default="rbf",
        help="Kernel for the SVR model.",
    )
    parser.add_argument("--svr-c", type=float, default=10.0, help="Penalty term for SVR.")
    parser.add_argument("--svr-epsilon", type=float, default=0.01, help="Epsilon-insensitive loss width.")
    parser.add_argument("--hybrid-svr-c", type=float, default=20.0, help="SVR C for hybrid model.")
    parser.add_argument(
        "--hybrid-svr-epsilon",
        type=float,
        default=0.01,
        help="SVR epsilon for hybrid model.",
    )
    return parser


def run_cli(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args.bp_split = min(max(args.bp_split, 0.1), 0.95)

    series_type = (
        FailureSeriesType.from_string(args.series_type)
        if args.series_type is not None
        else None
    )

    if args.load_experiment:
        try:
            loaded = load_experiment_zip(args.load_experiment)
        except Exception as exc:
            print(f"[ZDP] Failed to load experiment: {exc}", file=stderr)
            return 1

        ranked = loaded.ranked_results
        if not ranked:
            print("[ZDP] No model results found in experiment.", file=stderr)
            return 4

        show_cv = any(any(k.startswith("cv_") for k in item.result.metrics.keys()) for item in ranked)
        if show_cv:
            header = f"{'#':>2}  {'Model':<20}  {'CV_RMSE':>10}  {'CV_MAE':>10}  {'CV_R^2':>8}"
        else:
            header = f"{'#':>2}  {'Model':<20}  {'RMSE':>10}  {'MAE':>10}  {'R^2':>8}"
        print(header, file=stdout)
        print("-" * len(header), file=stdout)
        for item in ranked:
            metrics = item.result.metrics
            print(
                (
                    f"{item.rank:>2}  {item.result.model_name:<20}  "
                    f"{metrics.get('cv_rmse', float('nan')):>10.4f}  "
                    f"{metrics.get('cv_mae', float('nan')):>10.4f}  "
                    f"{metrics.get('cv_r2', float('nan')):>8.4f}"
                    if show_cv
                    else f"{item.rank:>2}  {item.result.model_name:<20}  "
                    f"{metrics.get('rmse', float('nan')):>10.4f}  "
                    f"{metrics.get('mae', float('nan')):>10.4f}  "
                    f"{metrics.get('r2', float('nan')):>8.4f}"
                ),
                file=stdout,
            )

        if args.report:
            try:
                output_path = Path(args.report)
                builder = ReportBuilder()
                builder.build(loaded.dataset, ranked, output_path=output_path)
                print(f"[ZDP] Report exported to {output_path}", file=stdout)
            except Exception as exc:  # pragma: no cover - external deps
                print(f"[ZDP] Failed to export report: {exc}", file=stderr)
                return 5

        return 0

    if not args.path:
        print("[ZDP] Missing dataset path (or use --load-experiment).", file=stderr)
        return 2

    try:
        dataset = load_failure_data(
            args.path,
            series_type=series_type,
            time_column=args.time_column,
            value_column=args.value_column,
        )
    except Exception as exc:  # pragma: no cover - argparse ensures usage
        print(f"[ZDP] Failed to load dataset: {exc}", file=stderr)
        return 1

    registry = _build_model_registry(args)
    default_models = ["jm", "go", "gm", "s-shaped", "svr", "bp", "hybrid"]
    requested = args.models or default_models
    resolved_factories: list[ModelFactory] = []
    for key in requested:
        key_lower = key.lower()
        entry = registry.get(key_lower)
        if entry is None:
            print(f"[ZDP] Unknown model identifier '{key}'.", file=stderr)
            return 2
        resolved_factories.append(entry[1])

    selected_models: list[ReliabilityModel] = []
    incompatible: list[str] = []
    for factory in resolved_factories:
        model = factory()
        if model.supports(dataset.series_type):
            selected_models.append(model)
        else:
            incompatible.append(model.name)

    if incompatible:
        print(
            "[ZDP] Skipping incompatible models for dataset type: "
            + ", ".join(incompatible),
            file=stderr,
        )
    if not selected_models:
        print("[ZDP] No compatible models available for the provided dataset.", file=stderr)
        return 3

    if args.include_plugins:
        plugin_factories = load_plugin_model_factories()
        for factory in plugin_factories:
            try:
                plugin_model = factory()
            except Exception:
                continue
            if plugin_model.supports(dataset.series_type):
                selected_models.append(plugin_model)

    service = AnalysisService(selected_models)

    validation = WalkForwardConfig(
        enabled=bool(args.walk_forward),
        min_train_size=(args.cv_min_train if args.cv_min_train and args.cv_min_train > 0 else None),
        horizon=max(1, int(args.cv_horizon)),
    )
    rank_by = args.rank_by.strip() or None
    pi_alpha = None
    if args.prediction_interval_alpha is not None and args.prediction_interval_alpha > 0:
        pi_alpha = float(args.prediction_interval_alpha)

    ranked = service.run(
        dataset,
        validation=validation,
        rank_by=rank_by,
        prediction_interval_alpha=pi_alpha,
    )
    if not ranked:
        print("[ZDP] No model results generated.", file=stderr)
        return 4

    show_cv = any(any(k.startswith("cv_") for k in item.result.metrics.keys()) for item in ranked)
    if show_cv:
        header = f"{'#':>2}  {'Model':<20}  {'CV_RMSE':>10}  {'CV_MAE':>10}  {'CV_R^2':>8}"
    else:
        header = f"{'#':>2}  {'Model':<20}  {'RMSE':>10}  {'MAE':>10}  {'R^2':>8}"
    print(header, file=stdout)
    print("-" * len(header), file=stdout)
    for item in ranked:
        metrics = item.result.metrics
        print(
            (
                f"{item.rank:>2}  {item.result.model_name:<20}  "
                f"{metrics.get('cv_rmse', float('nan')):>10.4f}  "
                f"{metrics.get('cv_mae', float('nan')):>10.4f}  "
                f"{metrics.get('cv_r2', float('nan')):>8.4f}"
                if show_cv
                else f"{item.rank:>2}  {item.result.model_name:<20}  "
                f"{metrics['rmse']:>10.4f}  {metrics['mae']:>10.4f}  {metrics['r2']:>8.4f}"
            ),
            file=stdout,
        )
        params = []
        for key, value in item.result.parameters.items():
            if isinstance(value, (int, float)) and not np.isnan(value):
                params.append(f"{key}={value:.4f}")
            else:
                params.append(f"{key}={value}")
        params_str = ", ".join(params)
        print(f"     parameters: {params_str}", file=stdout)

    if args.report:
        try:
            output_path = Path(args.report)
            builder = ReportBuilder()
            builder.build(dataset, ranked, output_path=output_path)
            print(f"[ZDP] Report exported to {output_path}", file=stdout)
        except Exception as exc:  # pragma: no cover - external deps
            print(f"[ZDP] Failed to export report: {exc}", file=stderr)
            return 5

    if args.export_experiment:
        try:
            zip_path = Path(args.export_experiment)
            cfg = default_experiment_config(
                dataset,
                ranking_metric=rank_by,
                walk_forward={
                    "enabled": bool(validation.enabled),
                    "min_train_size": validation.min_train_size,
                    "horizon": validation.horizon,
                },
                prediction_interval_alpha=pi_alpha,
            )
            export_experiment_zip(dataset, ranked, output_path=zip_path, config=cfg)
            print(f"[ZDP] Experiment exported to {zip_path}", file=stdout)
        except Exception as exc:
            print(f"[ZDP] Failed to export experiment: {exc}", file=stderr)
            return 6

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
