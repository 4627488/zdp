"""PySide6 main window wiring the ZDP workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np
from PySide6.QtGui import QAction
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
    QSpinBox,
)

from zdp.data import FailureDataset, FailureSeriesType, load_failure_data
from zdp.models import (
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
)
from zdp.reporting import ReportBuilder
from zdp.services import AnalysisService, RankedModelResult
from zdp.services import WalkForwardConfig
from zdp.visualization import (
    MatplotlibCanvas,
    plot_prediction_overview,
    plot_residuals,
    plot_u_plot,
    plot_y_plot,
)

from zdp.gui.experiment_window import ExperimentReplayWindow


class AnalysisWorker(QObject):
    """Background worker executing the AnalysisService."""

    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        dataset: FailureDataset,
        factories: Sequence[Callable[[], ReliabilityModel]],
        *,
        validation: WalkForwardConfig,
        prediction_interval_alpha: float | None,
        rank_by: str | None,
    ) -> None:
        super().__init__()
        self._dataset = dataset
        self._factories = list(factories)
        self._validation = validation
        self._prediction_interval_alpha = prediction_interval_alpha
        self._rank_by = rank_by

    @Slot()
    def run(self) -> None:
        try:
            models = [factory() for factory in self._factories]
            service = AnalysisService(models)
            results = service.run(
                self._dataset,
                validation=self._validation,
                prediction_interval_alpha=self._prediction_interval_alpha,
                rank_by=self._rank_by,
            )
            self.completed.emit(results)
        except Exception as exc:  # pragma: no cover - GUI runtime
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


@dataclass
class ModelDescriptor:
    key: str
    label: str
    description: str
    factory: Callable[[], ReliabilityModel]


class MainWindow(QMainWindow):
    """Desktop shell implementing the ZDP workflow."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("软件可靠性分析系统")
        self.resize(1400, 900)

        self.dataset: FailureDataset | None = None
        self.analysis_results: list[RankedModelResult] = []
        self._worker_thread: QThread | None = None
        self._model_checkboxes: dict[str, QCheckBox] = {}
        self._experiment_window: ExperimentReplayWindow | None = None

        self._build_ui()
        self._install_menu_bar()
        self._install_status_bar()

    def _install_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("文件")

        open_experiment = QAction("实验回放…", self)
        open_experiment.triggered.connect(self._open_experiment_replay)
        file_menu.addAction(open_experiment)

    @Slot()
    def _open_experiment_replay(self) -> None:
        if self._experiment_window is None:
            self._experiment_window = ExperimentReplayWindow()
        self._experiment_window.show()
        self._experiment_window.raise_()
        self._experiment_window.activateWindow()
        self._experiment_window.open_experiment_dialog()

    # ------------------------------------------------------------------
    # UI assembly
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
        layout.addWidget(self._build_data_group())
        layout.addWidget(self._build_models_group())
        layout.addWidget(self._build_parameters_group())
        layout.addWidget(self._build_actions_group())
        layout.addStretch()
        return panel

    def _build_data_group(self) -> QGroupBox:
        group = QGroupBox("数据导入")
        layout = QVBoxLayout(group)
        self.path_field = QLineEdit()
        self.path_field.setReadOnly(True)
        self.import_button = QPushButton("导入数据")
        self.import_button.clicked.connect(self._handle_import_clicked)
        self.data_preview = QPlainTextEdit()
        self.data_preview.setPlaceholderText("加载数据后将在此显示预览……")
        self.data_preview.setReadOnly(True)
        layout.addWidget(self.path_field)
        layout.addWidget(self.import_button)
        layout.addWidget(self.data_preview)
        return group

    def _build_models_group(self) -> QGroupBox:
        group = QGroupBox("模型库")
        vbox = QVBoxLayout(group)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        self._model_checkboxes.clear()
        for descriptor in self._model_descriptors():
            checkbox = QCheckBox(f"{descriptor.label} — {descriptor.description}")
            checkbox.setChecked(descriptor.key in {"go", "gm", "s-shaped", "svr", "bp"})
            checkbox.stateChanged.connect(self._update_parameter_visibility)
            self._model_checkboxes[descriptor.key] = checkbox
            container_layout.addWidget(checkbox)
        container_layout.addStretch()
        scroll_area.setWidget(container)
        vbox.addWidget(scroll_area)
        return group

    def _build_parameters_group(self) -> QGroupBox:
        group = QGroupBox("参数配置")
        layout = QVBoxLayout(group)

        # -----------------------------
        # Evaluation / ranking
        self.evaluation_group = QGroupBox("评估与排行")
        eval_form = QFormLayout(self.evaluation_group)

        self.walk_forward_check = QCheckBox("启用")
        self.walk_forward_check.setChecked(False)
        self.walk_forward_check.stateChanged.connect(self._update_parameter_visibility)
        eval_form.addRow("Walk-forward 验证", self.walk_forward_check)

        self.cv_horizon_spin = QSpinBox()
        self.cv_horizon_spin.setRange(1, 50)
        self.cv_horizon_spin.setValue(1)
        eval_form.addRow("CV 预测步长", self.cv_horizon_spin)

        self.cv_min_train_spin = QSpinBox()
        self.cv_min_train_spin.setRange(0, 1000000)
        self.cv_min_train_spin.setValue(0)
        eval_form.addRow("CV 最小训练(0自动)", self.cv_min_train_spin)

        layout.addWidget(self.evaluation_group)

        # -----------------------------
        # Prediction interval
        self.interval_group = QGroupBox("预测带")
        interval_form = QFormLayout(self.interval_group)

        self.enable_interval_check = QCheckBox("显示")
        self.enable_interval_check.setChecked(False)
        self.enable_interval_check.stateChanged.connect(self._update_parameter_visibility)
        interval_form.addRow("预测带", self.enable_interval_check)

        self.pi_alpha_spin = QDoubleSpinBox()
        self.pi_alpha_spin.setRange(0.01, 0.5)
        self.pi_alpha_spin.setSingleStep(0.01)
        self.pi_alpha_spin.setValue(0.05)
        interval_form.addRow("alpha", self.pi_alpha_spin)

        layout.addWidget(self.interval_group)

        # -----------------------------
        # SVR kernel (shared by SVR + Hybrid)
        self.kernel_group = QGroupBox("核函数")
        kernel_form = QFormLayout(self.kernel_group)
        self.svr_kernel_combo = QComboBox()
        self.svr_kernel_combo.addItems(["rbf", "poly", "linear", "sigmoid"])
        kernel_form.addRow("Kernel", self.svr_kernel_combo)
        layout.addWidget(self.kernel_group)

        # -----------------------------
        # SVR config
        self.svr_group = QGroupBox("SVR 参数")
        svr_form = QFormLayout(self.svr_group)
        self.svr_c_spin = QDoubleSpinBox()
        self.svr_c_spin.setRange(0.1, 1000.0)
        self.svr_c_spin.setValue(10.0)
        self.svr_c_spin.setSingleStep(1.0)
        svr_form.addRow("C", self.svr_c_spin)

        self.svr_epsilon_spin = QDoubleSpinBox()
        self.svr_epsilon_spin.setRange(0.001, 1.0)
        self.svr_epsilon_spin.setDecimals(3)
        self.svr_epsilon_spin.setValue(0.01)
        svr_form.addRow("Epsilon", self.svr_epsilon_spin)

        layout.addWidget(self.svr_group)

        # -----------------------------
        # Hybrid config
        self.hybrid_group = QGroupBox("混合模型参数")
        hybrid_form = QFormLayout(self.hybrid_group)
        self.hybrid_c_spin = QDoubleSpinBox()
        self.hybrid_c_spin.setRange(0.1, 1000.0)
        self.hybrid_c_spin.setValue(20.0)
        hybrid_form.addRow("SVR C", self.hybrid_c_spin)

        self.hybrid_epsilon_spin = QDoubleSpinBox()
        self.hybrid_epsilon_spin.setRange(0.001, 1.0)
        self.hybrid_epsilon_spin.setDecimals(3)
        self.hybrid_epsilon_spin.setValue(0.01)
        hybrid_form.addRow("SVR Epsilon", self.hybrid_epsilon_spin)

        layout.addWidget(self.hybrid_group)

        # -----------------------------
        # BP config
        self.bp_group = QGroupBox("BP 参数")
        bp_form = QFormLayout(self.bp_group)
        self.bp_hidden_spin = QSpinBox()
        self.bp_hidden_spin.setRange(4, 128)
        self.bp_hidden_spin.setValue(16)
        bp_form.addRow("隐藏节点", self.bp_hidden_spin)

        self.bp_epochs_spin = QSpinBox()
        self.bp_epochs_spin.setRange(50, 5000)
        self.bp_epochs_spin.setValue(800)
        bp_form.addRow("迭代次数", self.bp_epochs_spin)

        self.bp_lr_spin = QDoubleSpinBox()
        self.bp_lr_spin.setRange(0.0001, 1.0)
        self.bp_lr_spin.setDecimals(4)
        self.bp_lr_spin.setSingleStep(0.01)
        self.bp_lr_spin.setValue(0.01)
        bp_form.addRow("学习率", self.bp_lr_spin)

        self.bp_momentum_spin = QDoubleSpinBox()
        self.bp_momentum_spin.setRange(0.0, 0.99)
        self.bp_momentum_spin.setSingleStep(0.05)
        self.bp_momentum_spin.setValue(0.9)
        bp_form.addRow("动量", self.bp_momentum_spin)

        self.bp_split_spin = QDoubleSpinBox()
        self.bp_split_spin.setRange(0.5, 0.95)
        self.bp_split_spin.setSingleStep(0.05)
        self.bp_split_spin.setValue(0.8)
        bp_form.addRow("训练占比", self.bp_split_spin)

        layout.addWidget(self.bp_group)

        layout.addStretch()

        # Initial dependency-driven visibility
        self._update_parameter_visibility()
        return group

    @Slot()
    def _update_parameter_visibility(self) -> None:
        """Show only controls that are meaningful for current selections."""

        selected_keys = {key for key, cb in self._model_checkboxes.items() if cb.isChecked()}

        has_svr = "svr" in selected_keys
        has_hybrid = "hybrid" in selected_keys
        has_bp = "bp" in selected_keys

        # Model-specific blocks
        self.bp_group.setVisible(has_bp)
        self.svr_group.setVisible(has_svr)
        self.hybrid_group.setVisible(has_hybrid)
        self.kernel_group.setVisible(has_svr or has_hybrid)

        # Evaluation options: only show inner controls when enabled
        wf = self.walk_forward_check.isChecked()
        self.cv_horizon_spin.setEnabled(wf)
        self.cv_min_train_spin.setEnabled(wf)

        # Prediction interval: alpha only relevant when enabled
        show_interval = self.enable_interval_check.isChecked()
        self.pi_alpha_spin.setEnabled(show_interval)

    def _build_actions_group(self) -> QGroupBox:
        group = QGroupBox("执行")
        vbox = QVBoxLayout(group)
        self.run_button = QPushButton("运行分析")
        self.run_button.clicked.connect(self._handle_run_clicked)
        self.export_button = QPushButton("导出报告")
        self.export_button.clicked.connect(self._handle_export_clicked)
        self.export_button.setEnabled(False)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(150)
        vbox.addWidget(self.run_button)
        vbox.addWidget(self.export_button)
        vbox.addWidget(self.progress_bar)
        vbox.addWidget(QLabel("控制台"))
        vbox.addWidget(self.log_view)
        return group

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.metrics_table = QTableWidget(0, 7)
        self.metrics_table.setHorizontalHeaderLabels(["排名", "模型", "RMSE", "MAE", "R²", "AIC", "BIC"])
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.metrics_table)

        # 图表模型选择（用于残差、U、Y 图切换不同模型）
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

    def _install_status_bar(self) -> None:
        status_bar = QStatusBar()
        status_bar.showMessage("就绪")
        self.setStatusBar(status_bar)

    # ------------------------------------------------------------------
    # Data/model helpers
    def _model_descriptors(self) -> Iterable[ModelDescriptor]:
        return [
            ModelDescriptor("jm", "Jelinski-Moranda（JM）", "NHPP 间隔模型", lambda: JelinskiMorandaModel()),
            ModelDescriptor("go", "Goel-Okumoto（GO）", "NHPP 指数模型", lambda: GoelOkumotoModel()),
            ModelDescriptor("gm", "GM(1,1)", "灰色模型（累计）", lambda: GM11Model()),
            ModelDescriptor("s-shaped", "Yamada S 曲线", "适配 S 形增长", lambda: SShapedModel()),
            ModelDescriptor(
                "svr",
                "SVR 支持向量回归",
                "核回归",
                lambda: SupportVectorRegressionModel(
                    SVRConfig(
                        kernel=self.svr_kernel_combo.currentText(),
                        c=self.svr_c_spin.value(),
                        epsilon=self.svr_epsilon_spin.value(),
                    )
                ),
            ),
            ModelDescriptor(
                "bp",
                "BP 神经网络",
                "非线性神经网络",
                lambda: BPNeuralNetworkModel(
                    BPConfig(
                        hidden_size=self.bp_hidden_spin.value(),
                        epochs=self.bp_epochs_spin.value(),
                        learning_rate=self.bp_lr_spin.value(),
                        momentum=self.bp_momentum_spin.value(),
                        train_split=self.bp_split_spin.value(),
                    )
                ),
            ),
            ModelDescriptor(
                "hybrid",
                "EMD-SVR/GM 混合",
                "混合集成",
                lambda: EMDHybridModel(
                    HybridConfig(
                        svr_kernel=self.svr_kernel_combo.currentText(),
                        svr_c=self.hybrid_c_spin.value(),
                        svr_epsilon=self.hybrid_epsilon_spin.value(),
                    )
                ),
            ),
        ]

    def _selected_factories(self) -> list[Callable[[], ReliabilityModel]]:
        factories: list[Callable[[], ReliabilityModel]] = []
        descriptor_map = {desc.key: desc for desc in self._model_descriptors()}
        for key, checkbox in self._model_checkboxes.items():
            if checkbox.isChecked():
                descriptor = descriptor_map[key]
                factories.append(descriptor.factory)
        return factories

    # ------------------------------------------------------------------
    # Event handlers
    def _handle_import_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "选择故障数据集", str(Path.home()), "数据文件 (*.csv *.tsv *.txt *.xls *.xlsx)")
        if not file_path:
            return
        try:
            dataset = load_failure_data(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))
            return
        self.dataset = dataset
        self.path_field.setText(file_path)
        preview = np.array2string(dataset.values[: min(10, dataset.size)], separator=", ")
        self.data_preview.setPlainText(
            f"规模: {dataset.size}\n类型: {self._format_series_type(dataset.series_type)}\n预览: {preview}"
        )
        self._append_log(f"已加载数据集 '{file_path}'，共有 {dataset.size} 条记录")
        self.export_button.setEnabled(bool(self.analysis_results))

    def _handle_run_clicked(self) -> None:
        if self.dataset is None:
            QMessageBox.information(self, "缺少数据集", "请先导入故障数据。")
            return
        factories = self._selected_factories()
        if not factories:
            QMessageBox.information(self, "选择模型", "请至少选择一个模型再运行。")
            return
        self._append_log("开始运行分析……")
        self.run_button.setEnabled(False)
        self.progress_bar.show()

        validation = WalkForwardConfig(
            enabled=self.walk_forward_check.isChecked(),
            min_train_size=(
                self.cv_min_train_spin.value() if self.cv_min_train_spin.value() > 0 else None
            ),
            horizon=self.cv_horizon_spin.value(),
        )
        rank_by = None
        pi_alpha = self.pi_alpha_spin.value() if self.enable_interval_check.isChecked() else None

        worker = AnalysisWorker(
            self.dataset,
            factories,
            validation=validation,
            prediction_interval_alpha=pi_alpha,
            rank_by=rank_by,
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        worker.completed.connect(self._handle_analysis_completed)
        worker.failed.connect(self._handle_analysis_failed)
        worker.finished.connect(lambda: self._cleanup_thread(thread, worker))
        thread.started.connect(worker.run)
        self._worker_thread = thread
        thread.start()

    def _cleanup_thread(self, thread: QThread, worker: AnalysisWorker) -> None:
        thread.quit()
        thread.wait()
        worker.deleteLater()
        self._worker_thread = None
        self.progress_bar.hide()
        self.run_button.setEnabled(True)

    @Slot(object)
    def _handle_analysis_completed(self, results: Sequence[RankedModelResult]) -> None:
        self.analysis_results = list(results)
        if not results:
            QMessageBox.information(self, "无结果", "没有任何模型针对该数据集生成输出。")
            return
        self._append_log(f"分析完成，共运行 {len(results)} 个模型。")
        self._populate_metrics_table(results)
        self._refresh_plot_model_choices(results)
        self._update_plots()
        self.export_button.setEnabled(True)

    @Slot(str)
    def _handle_analysis_failed(self, message: str) -> None:
        QMessageBox.critical(self, "分析失败", message)
        self._append_log(f"分析失败：{message}")

    def _handle_export_clicked(self) -> None:
        if not self.dataset or not self.analysis_results:
            QMessageBox.information(self, "无可导出内容", "请先完成一次分析。")
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
            builder.build(self.dataset, self.analysis_results, output_path=output_path, figures=figures)
            self._append_log(f"报告已导出到 {output_path}")
            QMessageBox.information(self, "报告已导出", f"PDF 已保存至 {output_path}")
        except Exception as exc:  # pragma: no cover - depends on external libs
            QMessageBox.critical(self, "导出失败", str(exc))

    # ------------------------------------------------------------------
    # Rendering helpers
    def _populate_metrics_table(self, results: Sequence[RankedModelResult]) -> None:
        show_cv = any(
            any(key.startswith("cv_") for key in (ranked.result.metrics or {}).keys())
            for ranked in results
        )
        if show_cv:
            self.metrics_table.setColumnCount(7)
            self.metrics_table.setHorizontalHeaderLabels(["排名", "模型", "CV_RMSE", "CV_MAE", "CV_R²", "RMSE", "MAE"])
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
                item = QTableWidgetItem(value)
                self.metrics_table.setItem(row, col, item)

    def _update_plots(self) -> None:
        if not self.dataset:
            return
        if not self.analysis_results:
            for canvas in (self.prediction_canvas, self.residual_canvas, self.u_canvas, self.y_canvas):
                canvas.figure.clf()
                canvas.draw()
            return
        dataset = self.dataset
        results = self.analysis_results
        # 预测概览：展示所有模型（不再限制为前 3）
        self.prediction_canvas.draw_plot(
            lambda fig: plot_prediction_overview(fig, dataset, results, max_models=len(results))
        )
        # 残差 / U / Y 图：根据下拉框选择的模型绘制
        selected = self._selected_plot_result()
        if selected is None:
            selected = results[0]
        self.residual_canvas.draw_plot(lambda fig: plot_residuals(fig, dataset, selected))
        self.u_canvas.draw_plot(lambda fig: plot_u_plot(fig, dataset, selected))
        self.y_canvas.draw_plot(lambda fig: plot_y_plot(fig, dataset, selected))

    def _prepare_report_figures(self) -> dict[str, Figure]:
        from matplotlib.figure import Figure

        dataset = self.dataset
        results = self.analysis_results
        assert dataset and results
        selected = self._selected_plot_result() or results[0]
        figures: dict[str, Figure] = {}

        def build(builder: Callable[[Figure], None]) -> Figure:
            fig = Figure(figsize=(6, 4), dpi=120)
            builder(fig)
            return fig

        figures["预测概览"] = build(lambda fig: plot_prediction_overview(fig, dataset, results, max_models=len(results)))
        figures["残差分析"] = build(lambda fig: plot_residuals(fig, dataset, selected))
        figures["U 图"] = build(lambda fig: plot_u_plot(fig, dataset, selected))
        figures["Y 图"] = build(lambda fig: plot_y_plot(fig, dataset, selected))
        return figures

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _format_series_type(self, series_type: FailureSeriesType) -> str:
        mapping = {
            FailureSeriesType.TIME_BETWEEN_FAILURES: "故障间隔 (TBF)",
            FailureSeriesType.CUMULATIVE_FAILURES: "累计故障数",
        }
        return mapping.get(series_type, series_type.value)

    # ------------------------------------------------------------------
    # Plot selection helpers
    def _refresh_plot_model_choices(self, results: Sequence[RankedModelResult]) -> None:
        self.plot_model_combo.blockSignals(True)
        self.plot_model_combo.clear()
        for ranked in results:
            self.plot_model_combo.addItem(f"{ranked.rank}. {ranked.result.model_name}")
        self.plot_model_combo.setEnabled(True)
        self.plot_model_combo.setCurrentIndex(0)
        self.plot_model_combo.blockSignals(False)

    def _selected_plot_result(self) -> RankedModelResult | None:
        if not self.analysis_results:
            return None
        idx = self.plot_model_combo.currentIndex()
        if idx < 0 or idx >= len(self.analysis_results):
            return None
        return self.analysis_results[idx]
