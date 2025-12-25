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
)
from .reporting import ReportBuilder
from .services import AnalysisService

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
    parser.add_argument("path", help="Path to the CSV/Excel dataset containing failure data.")
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
    default_models = ["jm", "go", "s-shaped", "svr", "bp", "hybrid"]
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

    service = AnalysisService(selected_models)
    ranked = service.run(dataset)
    if not ranked:
        print("[ZDP] No model results generated.", file=stderr)
        return 4

    header = f"{'#':>2}  {'Model':<20}  {'RMSE':>10}  {'MAE':>10}  {'R^2':>8}"
    print(header, file=stdout)
    print("-" * len(header), file=stdout)
    for item in ranked:
        metrics = item.result.metrics
        print(
            f"{item.rank:>2}  {item.result.model_name:<20}  "
            f"{metrics['rmse']:>10.4f}  {metrics['mae']:>10.4f}  {metrics['r2']:>8.4f}",
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

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
