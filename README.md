# Software Reliability Analysis System (SRAS 2025)

This repository hosts the gradual implementation of a desktop-grade Software Reliability Analysis System inspired by the provided "软件可靠性分析课程设计" and "BP 神经网络" materials. The system targets a PySide6 desktop experience backed by Python's scientific ecosystem.

## Delivery Strategy

The implementation will follow incremental, reviewable milestones so each layer can be validated independently.

### Phase 0 — Project Bootstrap
- Configure Python tooling (virtual environment, dependency constraints, formatting/linting defaults).
- Scaffold the package layout (`sras/`) with placeholders for data IO, modeling, visualization, and reporting.
- Provide a minimum PySide6 entry point that opens a placeholder shell window.

### Phase 1 — Data Management Backbone
- Implement CSV/Excel ingestion helpers with schema inference for Time-Between-Failure (TBF) and cumulative-failure modes.
- Add preprocessing utilities: normalization, outlier detection hooks, exploratory plots.
- Expose the functionality via service objects decoupled from the GUI for testability.

### Phase 2 — Classical SRGM Implementations
- Implement Jelinski-Moranda (JM), Goel-Okumoto (GO/NHPP), and S-shaped models with SciPy-based parameter estimation.
- Provide shared interfaces (`ReliabilityModel`) with `fit`, `predict`, and `metrics` methods.
- Add statistical validation helpers (chi-square, K-S) and plotting adapters for U/Y plots.

### Phase 3 — AI/ML Model Suite
- Integrate PyTorch BP neural network module with configurable architecture and training loop instrumentation (loss curves, momentum, early stopping hooks).
- Integrate scikit-learn SVR (with kernel/parameter selection) and extend to hybrid workflows (e.g., EMD-SVR pipeline stub).
- Add dataset split/validation utilities (prequential, hold-out) and model ranking logic.

### Phase 4 — GUI Integration & User Workflow
- Build PySide6 views for the import → configure → run → explore → export workflow, wiring asynchronous workers for long-running fits.
- Embed Matplotlib or PyQtGraph canvases for real-time charts and progress reporting.
- Implement interactive model detail panes (parameters, metrics, residual diagnostics).

### Phase 5 — Reporting & Packaging
- Assemble PDF reporting templates (ReportLab layout engine) with project metadata, tables, and embedded figures.
- Provide export flows from the GUI plus CLI hooks for automated runs.
- Package the application for distribution (PyInstaller or briefcase) and document usage/testing instructions.

## Immediate Next Steps
1. Harden the dependency manifest (`pyproject.toml`) via lockfiles once the first features land.
2. Flesh out the Python package skeleton into concrete data/model services.
3. Commit bootstrap assets before moving into data ingestion and SRGM implementations.

## Project Layout

```
.
├── pyproject.toml          # Project + tooling configuration
├── README.md               # Roadmap and usage notes
├── src/
│   └── sras/
│       ├── __init__.py
│       ├── __main__.py    # Supports `python -m sras`
│       ├── app.py         # Qt application factory & runner
│       ├── data/          # (stub) ingestion utilities
│       ├── gui/
│       │   └── main_window.py
│       ├── models/        # (stub) SRGM + AI models
│       ├── reporting/     # (stub) PDF export helpers
│       ├── services/      # (stub) orchestration layers
│       └── visualization/ # (stub) plotting helpers
└── tests/
	 └── test_app.py
```

## Getting Started (uv workflow)
1. Install dependencies into an isolated environment:
	- `uv sync --all-extras`
2. Launch the placeholder desktop shell:
	- `uv run sras`
3. Run the smoke tests:
	- `uv run pytest`
4. Run the headless CLI on a dataset:
	- `uv run sras-cli data/ntds.csv --time-column t --value-column failures --report report.pdf`

The current GUI is fully wired: import data, select models, launch threaded analyses, inspect interactive plots, and export polished PDF reports directly from the desktop shell.

## Core APIs (Phase 1 deliverables)
- [sras.data](src/sras/data/__init__.py) exposes `FailureDataset`, `FailureSeriesType`, and `load_failure_data()` for CSV/Excel ingestion plus normalization/outlier helpers.
- [sras.models](src/sras/models/__init__.py) now includes `ReliabilityModel`, `JelinskiMorandaModel`, and `GoelOkumotoModel` with SciPy-backed parameter estimation and MAE/RMSE/$R^2$ metrics.
- [sras.services.analysis](src/sras/services/analysis.py) offers an `AnalysisService` that batches compatible models, runs them asynchronously, and ranks results by RMSE—ready to be wired into the UI.
- [sras.cli](src/sras/cli.py) surfaces the same orchestration flow via a headless `sras-cli` command, ideal for scripting regression experiments while the GUI matures.
- [sras.visualization](src/sras/visualization/__init__.py) provides embedded Matplotlib canvases plus builders for prediction, residual, and $U/Y$ diagnostics.
- [sras.reporting](src/sras/reporting/report_builder.py) renders ReportLab-powered PDF reports with tables and embedded figures.

## Feature Highlights
- **Model coverage:** JM, GO, Yamada S-shaped, SVR, BP 神经网络 (PyTorch), and a configurable EMD-SVR/GM hybrid ensemble.
- **Advanced metrics:** Each fit reports RMSE/MAE/$R^2$/MAPE, Chi-square, K-S, AIC, and BIC for side-by-side comparisons.
- **Visual analytics:** Prediction overlays, residual bars, and $U/Y$ plots update dynamically inside the PySide6 shell.
- **Automation:** The CLI mirrors the GUI workflow, supports hyper-parameter overrides, and can emit professional PDF reports headlessly.
- **Reporting:** ReportLab layouts capture dataset metadata, leaderboards, best-model diagnostics, and optional figures without extra native dependencies.

## GUI Workflow
1. **Import data** via the left panel (CSV/Excel, automatic schema inference). Preview shows size/type/sample rows.
2. **Select models** from the scrollable list and tweak hyper-parameters (BP nodes/epochs, SVR kernel/C/ε, hybrid SVR settings).
3. **Run Analysis** to launch the threaded pipeline; ranked metrics populate the table while plots refresh in real time.
4. **Inspect diagnostics** through tabs (Predictions, Residuals, U-Plot, Y-Plot) to validate distributional assumptions.
5. **Export Report** to generate a PDF with tables plus embedded plots for archival or coursework submission.

## CLI Examples
- Run only JM & GO: `uv run sras-cli data.csv --model jm --model go`
- Tune SVR and export report: `uv run sras-cli data.csv --svr-kernel poly --svr-c 50 --report sras.pdf`
- Accelerate BP training: `uv run sras-cli data.csv --bp-hidden 12 --bp-epochs 400 --bp-lr 0.05`
