"""Experiment replay window.

Loads an exported experiment ZIP (dataset/config/results) and presents the leaderboard
and plots. This is designed to be a separate window so users can compare analyses
without overwriting the main workflow.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from zdp.data import FailureDataset, FailureSeriesType
from zdp.reporting import ReportBuilder
from zdp.services import LoadedExperiment, RankedModelResult, load_experiment_zip
from zdp.visualization import (
    MatplotlibCanvas,
    plot_prediction_overview,
    plot_residuals,
    plot_u_plot,
    plot_y_plot,
)

if TYPE_CHECKING:
    from matplotlib.figure import Figure


class ExperimentReplayWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("实验回放")
        self.resize(1300, 850)

        self._loaded: LoadedExperiment | None = None
        self.dataset: FailureDataset | None = None
        self.results: list[RankedModelResult] = []

        self._build_ui()

    def _build_ui(self) -> None:
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        pkg_group = QGroupBox("实验包")
        pkg_layout = QVBoxLayout(pkg_group)

        self.path_field = QLineEdit()
        self.path_field.setReadOnly(True)
        pkg_layout.addWidget(self.path_field)

        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self.open_button = QPushButton("打开实验包")
        self.open_button.clicked.connect(self.open_experiment_dialog)
        self.export_button = QPushButton("导出报告")
        self.export_button.clicked.connect(self._handle_export_clicked)
        self.export_button.setEnabled(False)
        btn_layout.addWidget(self.open_button)
        btn_layout.addWidget(self.export_button)
        pkg_layout.addWidget(btn_row)

        self.info_view = QPlainTextEdit()
        self.info_view.setReadOnly(True)
        self.info_view.setPlaceholderText("打开实验包后将在此显示配置与摘要……")
        self.info_view.setMaximumHeight(220)
        pkg_layout.addWidget(QLabel("实验摘要"))
        pkg_layout.addWidget(self.info_view)

        layout.addWidget(pkg_group)
        layout.addStretch()
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.metrics_table = QTableWidget(0, 7)
        self.metrics_table.setHorizontalHeaderLabels(["排名", "模型", "RMSE", "MAE", "R²", "AIC", "BIC"])
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.metrics_table)

        selector_row = QWidget()
        selector_layout = QHBoxLayout(selector_row)
        selector_layout.setContentsMargins(0, 0, 0, 0)
        selector_layout.addWidget(QLabel("图表模型"))
        self.plot_model_combo = QComboBox()
        self.plot_model_combo.setEnabled(False)
        self.plot_model_combo.currentIndexChanged.connect(self._update_plots)
        selector_layout.addWidget(self.plot_model_combo)
        selector_layout.addStretch()
        layout.addWidget(selector_row)

        self.plot_tabs = QTabWidget()
        self.prediction_canvas = MatplotlibCanvas()
        self.residual_canvas = MatplotlibCanvas()
        self.u_canvas = MatplotlibCanvas()
        self.y_canvas = MatplotlibCanvas()

        self.plot_tabs.addTab(self._wrap_canvas(self.prediction_canvas), "预测曲线")
        self.plot_tabs.addTab(self._wrap_canvas(self.residual_canvas), "残差分析")
        self.plot_tabs.addTab(self._wrap_canvas(self.u_canvas), "U 图")
        self.plot_tabs.addTab(self._wrap_canvas(self.y_canvas), "Y 图")
        layout.addWidget(self.plot_tabs)
        return panel

    def _wrap_canvas(self, canvas: MatplotlibCanvas) -> QWidget:
        wrapper = QWidget()
        vbox = QVBoxLayout(wrapper)
        vbox.addWidget(canvas)
        return wrapper

    # ------------------------------------------------------------------
    # Public entrypoints
    @Slot()
    def open_experiment_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "打开实验包",
            str(Path.home()),
            "实验包 (*.zip)",
        )
        if not path:
            return
        self.load_experiment(path)

    def load_experiment(self, path: str | Path) -> None:
        try:
            loaded = load_experiment_zip(path)
        except Exception as exc:
            QMessageBox.critical(self, "加载失败", str(exc))
            return

        self._loaded = loaded
        self.dataset = loaded.dataset
        self.results = list(loaded.ranked_results)
        self.path_field.setText(str(path))
        self.export_button.setEnabled(bool(self.results))

        self._populate_info_view(loaded)
        self._populate_metrics_table(self.results)
        self._refresh_plot_model_choices(self.results)
        self._update_plots()

    # ------------------------------------------------------------------
    # Export
    def _handle_export_clicked(self) -> None:
        if not self.dataset or not self.results:
            QMessageBox.information(self, "无可导出内容", "请先打开一个实验包。")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 PDF 报告",
            str(Path.home() / "zdp-report.pdf"),
            "PDF 文件 (*.pdf)",
        )
        if not output_path:
            return

        figures = self._prepare_report_figures()
        try:
            builder = ReportBuilder()
            builder.build(self.dataset, self.results, output_path=output_path, figures=figures)
            QMessageBox.information(self, "报告已导出", f"PDF 已保存至 {output_path}")
        except Exception as exc:  # pragma: no cover - depends on external libs
            QMessageBox.critical(self, "导出失败", str(exc))

    # ------------------------------------------------------------------
    # Rendering
    def _populate_info_view(self, loaded: LoadedExperiment) -> None:
        cfg = loaded.config
        lines: list[str] = []
        lines.append(f"created_at: {cfg.created_at}")
        lines.append(f"series_type: {cfg.series_type}")
        lines.append(f"ranking_metric: {cfg.ranking_metric}")
        lines.append(f"prediction_interval_alpha: {cfg.prediction_interval_alpha}")
        lines.append("walk_forward: " + json.dumps(cfg.walk_forward, ensure_ascii=False))
        if cfg.dataset_metadata:
            lines.append("dataset_metadata: " + json.dumps(cfg.dataset_metadata, ensure_ascii=False))

        if self.dataset is not None:
            lines.append("")
            lines.append(f"records: {self.dataset.size}")
            lines.append(f"time_range: {self.dataset.time_axis[0]:.4f} -> {self.dataset.time_axis[-1]:.4f}")
            lines.append(f"series_type_label: {self._format_series_type(self.dataset.series_type)}")

        self.info_view.setPlainText("\n".join(lines))

    def _populate_metrics_table(self, results: list[RankedModelResult]) -> None:
        show_cv = any(
            any(key.startswith("cv_") for key in (ranked.result.metrics or {}).keys())
            for ranked in results
        )
        if show_cv:
            self.metrics_table.setColumnCount(7)
            self.metrics_table.setHorizontalHeaderLabels(
                ["排名", "模型", "CV_RMSE", "CV_MAE", "CV_R²", "RMSE", "MAE"]
            )
        else:
            self.metrics_table.setColumnCount(7)
            self.metrics_table.setHorizontalHeaderLabels(["排名", "模型", "RMSE", "MAE", "R²", "AIC", "BIC"])

        self.metrics_table.setRowCount(len(results))
        for row, ranked in enumerate(results):
            model_metrics = ranked.result.metrics
            if show_cv:
                entries = [
                    str(ranked.rank),
                    ranked.result.model_name,
                    f"{model_metrics.get('cv_rmse', float('nan')):.4f}",
                    f"{model_metrics.get('cv_mae', float('nan')):.4f}",
                    f"{model_metrics.get('cv_r2', float('nan')):.4f}",
                    f"{model_metrics.get('rmse', float('nan')):.4f}",
                    f"{model_metrics.get('mae', float('nan')):.4f}",
                ]
            else:
                entries = [
                    str(ranked.rank),
                    ranked.result.model_name,
                    f"{model_metrics.get('rmse', 0):.4f}",
                    f"{model_metrics.get('mae', 0):.4f}",
                    f"{model_metrics.get('r2', 0):.4f}",
                    f"{model_metrics.get('aic', 0):.2f}",
                    f"{model_metrics.get('bic', 0):.2f}",
                ]
            for col, value in enumerate(entries):
                self.metrics_table.setItem(row, col, QTableWidgetItem(value))

    def _update_plots(self) -> None:
        if not self.dataset:
            return
        if not self.results:
            for canvas in (self.prediction_canvas, self.residual_canvas, self.u_canvas, self.y_canvas):
                canvas.figure.clf()
                canvas.draw()
            return

        dataset = self.dataset
        results = self.results
        self.prediction_canvas.draw_plot(
            lambda fig: plot_prediction_overview(fig, dataset, results, max_models=len(results))
        )

        selected = self._selected_plot_result() or results[0]
        self.residual_canvas.draw_plot(lambda fig: plot_residuals(fig, dataset, selected))
        self.u_canvas.draw_plot(lambda fig: plot_u_plot(fig, dataset, selected))
        self.y_canvas.draw_plot(lambda fig: plot_y_plot(fig, dataset, selected))

    def _prepare_report_figures(self) -> dict[str, Figure]:
        from matplotlib.figure import Figure

        dataset = self.dataset
        results = self.results
        assert dataset and results
        selected = self._selected_plot_result() or results[0]

        figures: dict[str, Figure] = {}

        def build(builder: Callable[[Figure], None]) -> Figure:
            fig = Figure(figsize=(6, 4), dpi=120)
            builder(fig)
            return fig

        figures["预测概览"] = build(
            lambda fig: plot_prediction_overview(fig, dataset, results, max_models=len(results))
        )
        figures["残差分析"] = build(lambda fig: plot_residuals(fig, dataset, selected))
        figures["U 图"] = build(lambda fig: plot_u_plot(fig, dataset, selected))
        figures["Y 图"] = build(lambda fig: plot_y_plot(fig, dataset, selected))
        return figures

    def _refresh_plot_model_choices(self, results: list[RankedModelResult]) -> None:
        self.plot_model_combo.blockSignals(True)
        self.plot_model_combo.clear()
        for ranked in results:
            self.plot_model_combo.addItem(f"{ranked.rank}. {ranked.result.model_name}")
        self.plot_model_combo.setEnabled(True)
        self.plot_model_combo.setCurrentIndex(0)
        self.plot_model_combo.blockSignals(False)

    def _selected_plot_result(self) -> RankedModelResult | None:
        if not self.results:
            return None
        idx = self.plot_model_combo.currentIndex()
        if idx < 0 or idx >= len(self.results):
            return None
        return self.results[idx]

    def _format_series_type(self, series_type: FailureSeriesType) -> str:
        mapping = {
            FailureSeriesType.TIME_BETWEEN_FAILURES: "故障间隔 (TBF)",
            FailureSeriesType.CUMULATIVE_FAILURES: "累计故障数",
        }
        return mapping.get(series_type, series_type.value)
