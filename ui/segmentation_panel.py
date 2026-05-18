from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGroupBox, QComboBox, QSpinBox,
    QDoubleSpinBox, QFileDialog, QTextEdit, QProgressBar,
    QCheckBox, QFrame
)
from PySide6.QtCore import Signal, Qt

from ui.styles.tokens import Colors
from ui.styles.components import GlassPanel


class SegmentationPanel(QWidget):
    """图像分割操作面板。"""

    segmentation_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(6, 6, 6, 6)

        # Wrap content in GlassPanel
        glass = GlassPanel(self, radius=10, opacity=0.06, border_opacity=0.06)
        glass_layout = QVBoxLayout(glass)
        glass_layout.setSpacing(12)
        glass_layout.setContentsMargins(12, 12, 12, 12)

        # Group box style
        group_style = f"""
            QGroupBox {{
                color: {Colors.ACCENT};
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                margin-top: 14px;
                padding-top: 20px;
                font-weight: 600;
                font-size: 12px;
                letter-spacing: 0.5px;
                background-color: transparent;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
            }}
        """

        # Model selection
        model_group = QGroupBox("模型选择")
        model_group.setStyleSheet(group_style)
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(10)
        model_layout.setContentsMargins(12, 20, 12, 12)

        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)

        # Model icon
        model_icon = QLabel("ML")
        model_icon.setStyleSheet("""
            font-size: 10px;
            font-weight: 700;
            color: #a78bfa;
            background: rgba(167, 139, 250, 0.12);
            border-radius: 4px;
            padding: 2px 6px;
            border: none;
        """)
        path_layout.addWidget(model_icon)

        self._model_path_label = QLabel("未选择模型")
        self._model_path_label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 13px;
            background: transparent;
        """)
        path_layout.addWidget(self._model_path_label, 1)

        self._browse_btn = QPushButton("浏览...")
        self._browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.06);
                color: {Colors.TEXT_BODY};
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.08);
                border-color: rgba(255, 255, 255, 0.12);
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        self._browse_btn.clicked.connect(self._browse_model)
        path_layout.addWidget(self._browse_btn)
        model_layout.addLayout(path_layout)

        glass_layout.addWidget(model_group)

        # Parameters
        param_group = QGroupBox("推理参数")
        param_group.setStyleSheet(group_style)
        param_layout = QVBoxLayout(param_group)
        param_layout.setSpacing(10)
        param_layout.setContentsMargins(12, 20, 12, 12)

        device_layout = QHBoxLayout()
        device_label = QLabel("计算设备:")
        device_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; font-weight: 500; background: transparent;")
        device_layout.addWidget(device_label)
        self._device_combo = QComboBox()
        self._device_combo.addItems(["自动", "CPU", "CUDA (GPU)"])
        device_layout.addWidget(self._device_combo)
        param_layout.addLayout(device_layout)

        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("阈值:")
        threshold_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; font-weight: 500; background: transparent;")
        threshold_layout.addWidget(threshold_label)
        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0.0, 1.0)
        self._threshold_spin.setDecimals(3)
        self._threshold_spin.setSingleStep(0.05)
        self._threshold_spin.setValue(0.5)
        threshold_layout.addWidget(self._threshold_spin)
        param_layout.addLayout(threshold_layout)

        self._overlay_check = QCheckBox("叠加显示分割结果")
        self._overlay_check.setChecked(True)
        param_layout.addWidget(self._overlay_check)

        glass_layout.addWidget(param_group)

        # Execute button
        self._run_btn = QPushButton("执行分割")
        self._run_btn.setObjectName("run_btn")
        self._run_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Colors.ACCENT_DIM}, stop:1 {Colors.ACCENT});
                color: {Colors.WHITE};
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0096c7, stop:1 {Colors.ACCENT_LIGHT});
            }}
            QPushButton:pressed {{
                background: {Colors.ACCENT_DIM};
            }}
        """)
        self._run_btn.clicked.connect(self._run_segmentation)
        glass_layout.addWidget(self._run_btn)

        # Progress
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        glass_layout.addWidget(self._progress)

        # Result log
        log_group = QGroupBox("执行日志")
        log_group.setStyleSheet(group_style)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(12, 20, 12, 12)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(100)
        log_layout.addWidget(self._log_text)
        glass_layout.addWidget(log_group)

        glass_layout.addStretch()

        layout.addWidget(glass)

        self._model_path = ""

    def _browse_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择模型文件", "", "PyTorch 模型 (*.pth *.pt);;所有文件 (*)"
        )
        if path:
            self._model_path = path
            import os
            self._model_path_label.setText(os.path.basename(path))
            self._model_path_label.setStyleSheet(f"""
                color: {Colors.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 500;
                background: transparent;
            """)

    def _run_segmentation(self):
        params = {
            "model_path": self._model_path,
            "device": self._device_combo.currentText(),
            "threshold": self._threshold_spin.value(),
            "overlay": self._overlay_check.isChecked(),
        }
        if not self._model_path:
            self._log_text.append("错误：请先选择模型文件")
            return
        self._log_text.append(f"开始分割，模型: {params['model_path']}")
        self.segmentation_requested.emit(params)

    def log(self, message: str):
        self._log_text.append(message)

    def set_progress(self, value: int):
        self._progress.setVisible(True)
        self._progress.setValue(value)
