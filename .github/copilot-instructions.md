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
- Models must implement `clone()` for multi-threaded evaluation (returns fresh instance with same config).
- Model names are exposed in CLI/GUI via `name` class attribute (e.g., `GoelOkumotoModel.name = "Goel-Okumoto"`).
- Always respect `FailureSeriesType` when querying dataset: TBF models use `failure_intervals()`, others use `cumulative_failures()`.

## Adding/changing a model (must update 3 places)

1. Implement model under `src/zdp/models/` as a `ReliabilityModel` subclass with `_fit()` override.
2. Export it in `src/zdp/models/__init__.py`.
3. Register it in both:
   - CLI registry in `src/zdp/cli.py` (`_build_model_registry()` + default model list)
   - GUI list in `src/zdp/gui/main_window.py` (`_model_descriptors()` + default checkbox state)
4. If model takes config, add config class and CLI args (see `BPConfig`, `SVRConfig` pattern).

## GUI threading + plotting

- GUI runs analysis in a `QThread` via `AnalysisWorker` (see `src/zdp/gui/main_window.py`).
- Worker lifecycle: `AnalysisWorker.run()` emits `completed()` signal on success, `failed()` on exception.
- Plot behavior is intentional:
  - Prediction overview shows _all_ successful models by calling
    `plot_prediction_overview(..., max_models=len(results))`.
  - Residual/U/Y plots use the "图表模型" combo selection (default best model).

## Plugin model system

- External models can be registered via Python entry points (`pyproject.toml`):
  ```toml
  [project.entry-points."zdp.models"]
  my_model = "some_pkg.module:MyModel"
  ```
- CLI loads plugins via `load_plugin_model_factories()` (`src/zdp/models/plugins.py`); entry point object can be a `ReliabilityModel` class or factory function.
- GUI currently does NOT auto-load plugins; plugins are CLI-only unless explicitly wired into `_model_descriptors()`.

## Experiment export/import for reproducibility

- `AnalysisService.run()` results can be exported as ZIP via `export_experiment_zip()` (`src/zdp/services/experiments.py`).
- ZIP contains: dataset (CSV), config (JSON), ranked results summary.
- Intentionally avoids pickling models; supports replay/reporting on different machines.

## Reporting

- PDF export uses `ReportBuilder` (`src/zdp/reporting/report_builder.py`) and requires `reportlab`.
- Figures are rendered to PNG via `zdp.visualization.figure_to_png_bytes()`.
- Chinese font registration is automatic; checks Windows system fonts (微软雅黑, 宋体, 黑体).

## Developer workflows (Windows + uv)

- Install: `uv sync --all-extras` (CI uses `--frozen`).
- Run GUI: `uv run zdp` or `python -m zdp`.
- Run CLI: `uv run zdp-cli data.csv --model go --report out.pdf`.
- Tests: `uv run pytest`.
- Formatting/linting: `uv run ruff check .` and `uv run black .` (line length 100).

## Packaging/release

- Windows single-file exe via PyInstaller: `uv run pyinstaller --noconfirm --clean zdp.spec`.
- PyInstaller entry uses `zdp_entry.py` with `multiprocessing.freeze_support()`.
