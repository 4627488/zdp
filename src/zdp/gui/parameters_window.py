"""Parameters configuration window.

Separate window for detailed model and analysis parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

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
from zdp.services import WalkForwardConfig


@dataclass
class ParametersState:
    """Current state of all parameters."""

    walk_forward_enabled: bool
    cv_min_train_size: int | None
    cv_horizon: int
    prediction_interval_enabled: bool
    pi_alpha: float

    svr_kernel: str
    svr_c: float
    svr_epsilon: float

    hybrid_c: float
    hybrid_epsilon: float

    bp_hidden: int
    bp_epochs: int
    bp_lr: float
    bp_momentum: float
    bp_split: float


class ParametersWindow(QDialog):
    """Modal/modeless dialog for parameter configuration."""

    parameters_changed = Signal(ParametersState)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("参数设置")
        self.resize(500, 700)
        self._current_state = ParametersState(
            walk_forward_enabled=False,
            cv_min_train_size=0,
            cv_horizon=1,
            prediction_interval_enabled=False,
            pi_alpha=0.05,
            svr_kernel="rbf",
            svr_c=10.0,
            svr_epsilon=0.01,
            hybrid_c=20.0,
            hybrid_epsilon=0.01,
            bp_hidden=32,
            bp_epochs=100,
            bp_lr=0.01,
            bp_momentum=0.9,
            bp_split=0.8,
        )
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)

        container_layout.addWidget(self._build_evaluation_group())
        container_layout.addWidget(self._build_interval_group())
        container_layout.addWidget(self._build_kernel_group())
        container_layout.addWidget(self._build_svr_group())
        container_layout.addWidget(self._build_hybrid_group())
        container_layout.addWidget(self._build_bp_group())
        container_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

        button_row = QWidget()
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._handle_ok)
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._handle_reset)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(reset_btn)
        layout.addWidget(button_row)

    def _build_evaluation_group(self) -> QGroupBox:
        group = QGroupBox("评估与排行")
        layout = QFormLayout(group)

        self.walk_forward_check = QCheckBox("启用")
        self.walk_forward_check.setChecked(self._current_state.walk_forward_enabled)
        self.walk_forward_check.stateChanged.connect(self._on_wf_toggled)
        layout.addRow("Walk-forward 验证", self.walk_forward_check)

        self.cv_horizon_spin = QSpinBox()
        self.cv_horizon_spin.setRange(1, 50)
        self.cv_horizon_spin.setValue(self._current_state.cv_horizon)
        layout.addRow("CV 预测步长", self.cv_horizon_spin)

        self.cv_min_train_spin = QSpinBox()
        self.cv_min_train_spin.setRange(0, 1000000)
        self.cv_min_train_spin.setValue(self._current_state.cv_min_train_size or 0)
        self.cv_min_train_spin.setEnabled(self._current_state.walk_forward_enabled)
        layout.addRow("CV 最小训练(0自动)", self.cv_min_train_spin)

        return group

    def _build_interval_group(self) -> QGroupBox:
        group = QGroupBox("预测带")
        layout = QFormLayout(group)

        self.enable_interval_check = QCheckBox("显示")
        self.enable_interval_check.setChecked(self._current_state.prediction_interval_enabled)
        self.enable_interval_check.stateChanged.connect(self._on_interval_toggled)
        layout.addRow("预测带", self.enable_interval_check)

        self.pi_alpha_spin = QDoubleSpinBox()
        self.pi_alpha_spin.setRange(0.01, 0.5)
        self.pi_alpha_spin.setSingleStep(0.01)
        self.pi_alpha_spin.setValue(self._current_state.pi_alpha)
        self.pi_alpha_spin.setEnabled(self._current_state.prediction_interval_enabled)
        layout.addRow("alpha", self.pi_alpha_spin)

        return group

    def _build_kernel_group(self) -> QGroupBox:
        group = QGroupBox("核函数")
        layout = QFormLayout(group)
        self.svr_kernel_combo = QComboBox()
        self.svr_kernel_combo.addItems(["rbf", "poly", "linear", "sigmoid"])
        self.svr_kernel_combo.setCurrentText(self._current_state.svr_kernel)
        layout.addRow("Kernel", self.svr_kernel_combo)
        return group

    def _build_svr_group(self) -> QGroupBox:
        group = QGroupBox("SVR 参数")
        layout = QFormLayout(group)

        self.svr_c_spin = QDoubleSpinBox()
        self.svr_c_spin.setRange(0.1, 1000.0)
        self.svr_c_spin.setValue(self._current_state.svr_c)
        self.svr_c_spin.setSingleStep(1.0)
        layout.addRow("C", self.svr_c_spin)

        self.svr_epsilon_spin = QDoubleSpinBox()
        self.svr_epsilon_spin.setRange(0.001, 1.0)
        self.svr_epsilon_spin.setDecimals(3)
        self.svr_epsilon_spin.setValue(self._current_state.svr_epsilon)
        layout.addRow("Epsilon", self.svr_epsilon_spin)

        return group

    def _build_hybrid_group(self) -> QGroupBox:
        group = QGroupBox("混合模型参数")
        layout = QFormLayout(group)

        self.hybrid_c_spin = QDoubleSpinBox()
        self.hybrid_c_spin.setRange(0.1, 1000.0)
        self.hybrid_c_spin.setValue(self._current_state.hybrid_c)
        layout.addRow("SVR C", self.hybrid_c_spin)

        self.hybrid_epsilon_spin = QDoubleSpinBox()
        self.hybrid_epsilon_spin.setRange(0.001, 1.0)
        self.hybrid_epsilon_spin.setDecimals(3)
        self.hybrid_epsilon_spin.setValue(self._current_state.hybrid_epsilon)
        layout.addRow("SVR Epsilon", self.hybrid_epsilon_spin)

        return group

    def _build_bp_group(self) -> QGroupBox:
        group = QGroupBox("BP 神经网络参数")
        layout = QFormLayout(group)

        self.bp_hidden_spin = QSpinBox()
        self.bp_hidden_spin.setRange(1, 512)
        self.bp_hidden_spin.setValue(self._current_state.bp_hidden)
        layout.addRow("隐层", self.bp_hidden_spin)

        self.bp_epochs_spin = QSpinBox()
        self.bp_epochs_spin.setRange(1, 10000)
        self.bp_epochs_spin.setValue(self._current_state.bp_epochs)
        layout.addRow("轮数", self.bp_epochs_spin)

        self.bp_lr_spin = QDoubleSpinBox()
        self.bp_lr_spin.setRange(0.0001, 0.1)
        self.bp_lr_spin.setDecimals(4)
        self.bp_lr_spin.setValue(self._current_state.bp_lr)
        layout.addRow("学习率", self.bp_lr_spin)

        self.bp_momentum_spin = QDoubleSpinBox()
        self.bp_momentum_spin.setRange(0.0, 1.0)
        self.bp_momentum_spin.setDecimals(2)
        self.bp_momentum_spin.setValue(self._current_state.bp_momentum)
        layout.addRow("动量", self.bp_momentum_spin)

        self.bp_split_spin = QDoubleSpinBox()
        self.bp_split_spin.setRange(0.0, 1.0)
        self.bp_split_spin.setDecimals(2)
        self.bp_split_spin.setSingleStep(0.05)
        self.bp_split_spin.setValue(self._current_state.bp_split)
        layout.addRow("训练占比", self.bp_split_spin)

        return group

    @Slot()
    def _on_wf_toggled(self) -> None:
        enabled = self.walk_forward_check.isChecked()
        self.cv_horizon_spin.setEnabled(enabled)
        self.cv_min_train_spin.setEnabled(enabled)

    @Slot()
    def _on_interval_toggled(self) -> None:
        enabled = self.enable_interval_check.isChecked()
        self.pi_alpha_spin.setEnabled(enabled)

    @Slot()
    def _handle_ok(self) -> None:
        self._update_state_from_controls()
        self.parameters_changed.emit(self._current_state)
        self.close()

    @Slot()
    def _handle_reset(self) -> None:
        self._current_state = ParametersState(
            walk_forward_enabled=False,
            cv_min_train_size=0,
            cv_horizon=1,
            prediction_interval_enabled=False,
            pi_alpha=0.05,
            svr_kernel="rbf",
            svr_c=10.0,
            svr_epsilon=0.01,
            hybrid_c=20.0,
            hybrid_epsilon=0.01,
            bp_hidden=32,
            bp_epochs=100,
            bp_lr=0.01,
            bp_momentum=0.9,
            bp_split=0.8,
        )
        self._sync_controls_from_state()

    def _update_state_from_controls(self) -> None:
        self._current_state = ParametersState(
            walk_forward_enabled=self.walk_forward_check.isChecked(),
            cv_min_train_size=(
                self.cv_min_train_spin.value() if self.cv_min_train_spin.value() > 0 else None
            ),
            cv_horizon=self.cv_horizon_spin.value(),
            prediction_interval_enabled=self.enable_interval_check.isChecked(),
            pi_alpha=self.pi_alpha_spin.value(),
            svr_kernel=self.svr_kernel_combo.currentText(),
            svr_c=self.svr_c_spin.value(),
            svr_epsilon=self.svr_epsilon_spin.value(),
            hybrid_c=self.hybrid_c_spin.value(),
            hybrid_epsilon=self.hybrid_epsilon_spin.value(),
            bp_hidden=self.bp_hidden_spin.value(),
            bp_epochs=self.bp_epochs_spin.value(),
            bp_lr=self.bp_lr_spin.value(),
            bp_momentum=self.bp_momentum_spin.value(),
            bp_split=self.bp_split_spin.value(),
        )

    def _sync_controls_from_state(self) -> None:
        state = self._current_state
        self.walk_forward_check.setChecked(state.walk_forward_enabled)
        self.cv_min_train_spin.setValue(state.cv_min_train_size or 0)
        self.cv_horizon_spin.setValue(state.cv_horizon)
        self.enable_interval_check.setChecked(state.prediction_interval_enabled)
        self.pi_alpha_spin.setValue(state.pi_alpha)
        self.svr_kernel_combo.setCurrentText(state.svr_kernel)
        self.svr_c_spin.setValue(state.svr_c)
        self.svr_epsilon_spin.setValue(state.svr_epsilon)
        self.hybrid_c_spin.setValue(state.hybrid_c)
        self.hybrid_epsilon_spin.setValue(state.hybrid_epsilon)
        self.bp_hidden_spin.setValue(state.bp_hidden)
        self.bp_epochs_spin.setValue(state.bp_epochs)
        self.bp_lr_spin.setValue(state.bp_lr)
        self.bp_momentum_spin.setValue(state.bp_momentum)
        self.bp_split_spin.setValue(state.bp_split)
        self._on_wf_toggled()
        self._on_interval_toggled()

    def get_state(self) -> ParametersState:
        """Return current parameter state."""
        return self._current_state

    def set_state(self, state: ParametersState) -> None:
        """Load parameter state."""
        self._current_state = state
        self._sync_controls_from_state()


__all__ = ["ParametersWindow", "ParametersState"]
