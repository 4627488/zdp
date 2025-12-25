# Copilot instructions for ZDP

## Big picture (where to look)
- Package lives in `src/zdp/` (tests use `pythonpath = ["src"]` in `pyproject.toml`).
- Entry points:
  - GUI: `zdp` script → `zdp.app:run` (see `src/zdp/app.py`, `src/zdp/gui/main_window.py`).
  - CLI: `zdp-cli` script → `zdp.cli:main` (see `src/zdp/cli.py`).
  - Module run: `python -m zdp` → `src/zdp/__main__.py`.

## Core data flow
- Load data from CSV/Excel with inference: `zdp.data.load_failure_data()` in `src/zdp/data/loader.py`.
  - Time column is optional; if missing, uses `1..N`.
  - Series type inference: if `np.diff(values)` is all `>= 0` → cumulative failures; else → TBF.
- Data container is `FailureDataset` (`src/zdp/data/dataset.py`) with helpers:
  - `cumulative_failures()` and `failure_intervals()` convert representations.
- Models implement `ReliabilityModel` (`src/zdp/models/base.py`) and must return `ModelResult`.
- Orchestration/ranking is centralized in `AnalysisService` (`src/zdp/services/analysis.py`):
  - Runs only compatible models (`model.supports(dataset.series_type)`)
  - Sorts by `rmse` ascending and assigns ranks.

## Project-specific conventions
- Series-type compatibility matters:
  - `BPNeuralNetworkModel`, `SupportVectorRegressionModel`, `EMDHybridModel` require cumulative failures
    (`required_series_type = FailureSeriesType.CUMULATIVE_FAILURES`) and are skipped for TBF datasets.
- Metrics come from `ReliabilityModel.compute_metrics()`; keep shapes aligned and return keys consistent.

## Adding/changing a model (must update 3 places)
1) Implement model under `src/zdp/models/` as a `ReliabilityModel` subclass.
2) Export it in `src/zdp/models/__init__.py`.
3) Register it in both:
   - CLI registry in `src/zdp/cli.py` (`_build_model_registry()` + default model list)
   - GUI list in `src/zdp/gui/main_window.py` (`_model_descriptors()` + default checkbox state)

## GUI threading + plotting
- GUI runs analysis in a `QThread` via `AnalysisWorker` (see `src/zdp/gui/main_window.py`).
- Plot behavior is intentional:
  - Prediction overview shows *all* successful models by calling
    `plot_prediction_overview(..., max_models=len(results))`.
  - Residual/U/Y plots use the “图表模型” combo selection (default best model).

## Reporting
- PDF export uses `ReportBuilder` (`src/zdp/reporting/report_builder.py`) and requires `reportlab`.
- Figures are rendered to PNG via `zdp.visualization.figure_to_png_bytes()`.

## Developer workflows (Windows + uv)
- Install: `uv sync --all-extras` (CI uses `--frozen`).
- Run GUI: `uv run zdp` or `python -m zdp`.
- Run CLI: `uv run zdp-cli data.csv --model go --report out.pdf`.
- Tests: `uv run pytest`.
- Formatting/linting: `uv run ruff check .` and `uv run black .` (line length 100).

## Packaging/release
- Windows single-file exe via PyInstaller: `uv run pyinstaller --noconfirm --clean zdp.spec`.
- PyInstaller entry uses `zdp_entry.py` with `multiprocessing.freeze_support()`.