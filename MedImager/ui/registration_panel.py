from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGroupBox, QComboBox, QSpinBox,
    QDoubleSpinBox, QFileDialog, QTextEdit, QProgressBar,
    QCheckBox, QScrollArea, QFormLayout, QFrame
)
from PySide6.QtCore import Signal, Qt

from core.registration import WINDOW_SETTINGS
from ui.styles.tokens import Colors
from ui.styles.components import GlassPanel


class _ZSegmentWidget(QWidget):
    """一组 Z 分段输入控件：start_z, end_z, HU_min, HU_max。"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._rows: list[tuple[QSpinBox, QSpinBox, QSpinBox, QSpinBox, QPushButton]] = []
        header = QHBoxLayout()
        header.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 600;
            color: {Colors.TEXT_PRIMARY};
            background: transparent;
        """)
        header.addWidget(title_label)

        self._add_btn = QPushButton("+ 添加分段")
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.ACCENT};
                border: 1px solid {Colors.ACCENT_GLOW};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: rgba(0, 180, 216, 0.1);
                border-color: rgba(0, 180, 216, 0.5);
            }}
        """)
        self._add_btn.clicked.connect(self._add_row)
        header.addWidget(self._add_btn)
        header.addStretch()
        layout.addLayout(header)

        # 表头
        h = QHBoxLayout()
        h.setSpacing(6)
        for t in ["起始Z", "结束Z", "HU_min", "HU_max", ""]:
            lbl = QLabel(t)
            lbl.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED}; font-weight: 500; background: transparent;")
            h.addWidget(lbl)
        layout.addLayout(h)

        self._rows_layout = layout
        self._add_row()  # 默认一行

    def _add_row(self):
        row_layout = QHBoxLayout()
        row_layout.setSpacing(6)
        start_z = QSpinBox(); start_z.setRange(0, 99999); start_z.setValue(0)
        end_z = QSpinBox(); end_z.setRange(0, 99999); end_z.setValue(100)
        hu_min = QSpinBox(); hu_min.setRange(-3000, 3000); hu_min.setValue(-125)
        hu_max = QSpinBox(); hu_max.setRange(-3000, 3000); hu_max.setValue(225)
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.ERROR};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(239, 68, 68, 0.1);
                border-color: rgba(239, 68, 68, 0.3);
            }}
        """)

        for w in [start_z, end_z, hu_min, hu_max]:
            row_layout.addWidget(w)
        row_layout.addWidget(del_btn)

        self._rows_layout.addLayout(row_layout)
        widgets = (start_z, end_z, hu_min, hu_max, del_btn)
        self._rows.append(widgets)
        del_btn.clicked.connect(lambda: self._remove_row(widgets, row_layout))

    def _remove_row(self, widgets, layout):
        if len(self._rows) <= 1:
            return
        self._rows.remove(widgets)
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        layout.deleteLater()

    def get_segments(self) -> list[tuple[int, int, int, int]]:
        result = []
        for start_z, end_z, hu_min, hu_max, _ in self._rows:
            result.append((start_z.value(), end_z.value(), hu_min.value(), hu_max.value()))
        return result

    def set_segments(self, segments: list[tuple[int, int, int, int]]):
        while self._rows:
            widgets = self._rows[0]
            self._remove_row(widgets, None)
        for _ in segments:
            self._add_row()
        for i, (sz, ez, hmin, hmax) in enumerate(segments):
            if i < len(self._rows):
                self._rows[i][0].setValue(sz)
                self._rows[i][1].setValue(ez)
                self._rows[i][2].setValue(hmin)
                self._rows[i][3].setValue(hmax)


class RegistrationPanel(QWidget):
    """配准操作面板。"""

    registration_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_dir = ""

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        inner = GlassPanel(scroll, radius=10, opacity=0.06, border_opacity=0.06)
        layout = QVBoxLayout(inner)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # ---- Group box style ----
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

        # ---- 图像选择 (下拉框 + 浏览) ----
        file_group = QGroupBox("图像选择")
        file_group.setStyleSheet(group_style)
        file_layout = QFormLayout(file_group)
        file_layout.setSpacing(10)
        file_layout.setContentsMargins(12, 20, 12, 12)

        # 自动识别按钮
        auto_row = QHBoxLayout()
        self._auto_btn = QPushButton("自动识别目录文件")
        self._auto_btn.setObjectName("auto_btn")
        self._auto_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Colors.SUCCESS_DIM}, stop:1 {Colors.SUCCESS});
                color: {Colors.WHITE};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Colors.SUCCESS}, stop:1 #34d399);
            }}
            QPushButton:pressed {{
                background: #047857;
            }}
        """)
        self._auto_btn.clicked.connect(self._auto_detect_files)
        auto_row.addWidget(self._auto_btn)
        file_layout.addRow(auto_row)

        # Browse button style
        browse_style = f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.06);
                color: {Colors.TEXT_BODY};
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.10);
                border-color: rgba(255, 255, 255, 0.18);
            }}
        """

        self._fixed_combo = QComboBox()
        self._fixed_combo.addItem("（未选择）", "")
        self._fixed_combo.currentIndexChanged.connect(self._on_fixed_changed)
        fixed_row = QHBoxLayout()
        fixed_row.setSpacing(6)
        fixed_row.addWidget(self._fixed_combo, 1)
        self._fixed_browse = QPushButton("...")
        self._fixed_browse.setFixedSize(32, 32)
        self._fixed_browse.setStyleSheet(browse_style)
        self._fixed_browse.clicked.connect(lambda: self._browse_file("fixed"))
        fixed_row.addWidget(self._fixed_browse)
        file_layout.addRow("固定图像 (RTCT):", fixed_row)

        self._moving_combo = QComboBox()
        self._moving_combo.addItem("（未选择）", "")
        self._moving_combo.currentIndexChanged.connect(self._on_moving_changed)
        moving_row = QHBoxLayout()
        moving_row.setSpacing(6)
        moving_row.addWidget(self._moving_combo, 1)
        self._moving_browse = QPushButton("...")
        self._moving_browse.setFixedSize(32, 32)
        self._moving_browse.setStyleSheet(browse_style)
        self._moving_browse.clicked.connect(lambda: self._browse_file("moving"))
        moving_row.addWidget(self._moving_browse)
        file_layout.addRow("待配准图像 (CT):", moving_row)

        self._pet_combo = QComboBox()
        self._pet_combo.addItem("（无 / 不使用）", "")
        pet_row = QHBoxLayout()
        pet_row.setSpacing(6)
        pet_row.addWidget(self._pet_combo, 1)
        self._pet_browse = QPushButton("...")
        self._pet_browse.setFixedSize(32, 32)
        self._pet_browse.setStyleSheet(browse_style)
        self._pet_browse.clicked.connect(lambda: self._browse_file("pet"))
        pet_row.addWidget(self._pet_browse)
        file_layout.addRow("PET 图像 (可选):", pet_row)

        self._mask_combo = QComboBox()
        self._mask_combo.addItem("（无 / 不使用）", "")
        mask_row = QHBoxLayout()
        mask_row.setSpacing(6)
        mask_row.addWidget(self._mask_combo, 1)
        self._mask_browse = QPushButton("...")
        self._mask_browse.setFixedSize(32, 32)
        self._mask_browse.setStyleSheet(browse_style)
        self._mask_browse.clicked.connect(lambda: self._browse_file("mask"))
        mask_row.addWidget(self._mask_browse)
        file_layout.addRow("掩码文件 (可选):", mask_row)

        layout.addWidget(file_group)

        # ---- 窗位设置 ----
        window_group = QGroupBox("CT HU 窗位预处理")
        window_group.setStyleSheet(group_style)
        window_layout = QVBoxLayout(window_group)
        window_layout.setSpacing(10)
        window_layout.setContentsMargins(12, 20, 12, 12)

        win_row = QHBoxLayout()
        win_label = QLabel("解剖部位:")
        win_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; font-weight: 500; background: transparent;")
        win_row.addWidget(win_label)
        self._window_combo = QComboBox()
        self._window_combo.addItem("仅空气截断 (None)")
        for name in WINDOW_SETTINGS:
            wmin, wmax = WINDOW_SETTINGS[name]
            self._window_combo.addItem(f"{name} [{wmin}, {wmax}]")
        self._window_combo.setCurrentText("Lung [-750, 422]")
        win_row.addWidget(self._window_combo, 1)
        window_layout.addLayout(win_row)

        self._zseg_check = QCheckBox("启用 Z 轴分段窗位")
        self._zseg_check.toggled.connect(self._on_zseg_toggled)
        window_layout.addWidget(self._zseg_check)

        self._zseg_fixed = _ZSegmentWidget("固定图像 (RTCT) 分段:")
        self._zseg_fixed.setVisible(False)
        window_layout.addWidget(self._zseg_fixed)

        self._zseg_moving = _ZSegmentWidget("待配准图像 (CT) 分段:")
        self._zseg_moving.setVisible(False)
        window_layout.addWidget(self._zseg_moving)

        layout.addWidget(window_group)

        # ---- 仿射阶段参数 ----
        aff_group = QGroupBox("仿射阶段参数")
        aff_group.setStyleSheet(group_style)
        aff_layout = QFormLayout(aff_group)
        aff_layout.setSpacing(10)
        aff_layout.setContentsMargins(12, 20, 12, 12)

        self._aff_metric = QComboBox()
        self._aff_metric.addItems(["mattes", "meansquares", "gc"])
        aff_layout.addRow("度量:", self._aff_metric)

        self._aff_sampling = QSpinBox()
        self._aff_sampling.setRange(1, 1000)
        self._aff_sampling.setValue(100)
        aff_layout.addRow("直方图 bin 数:", self._aff_sampling)

        self._aff_iter = QTextEdit()
        self._aff_iter.setMaximumHeight(42)
        self._aff_iter.setPlainText("2100, 1200, 1200, 10")
        aff_layout.addRow("迭代次数:", self._aff_iter)

        self._aff_shrink = QTextEdit()
        self._aff_shrink.setMaximumHeight(42)
        self._aff_shrink.setPlainText("6, 4, 2, 1")
        aff_layout.addRow("缩放因子:", self._aff_shrink)

        self._aff_sigma = QTextEdit()
        self._aff_sigma.setMaximumHeight(42)
        self._aff_sigma.setPlainText("5, 4, 2, 1")
        aff_layout.addRow("平滑 sigma:", self._aff_sigma)

        layout.addWidget(aff_group)

        # ---- SyN 阶段参数 ----
        syn_group = QGroupBox("SyN 可变形阶段参数")
        syn_group.setStyleSheet(group_style)
        syn_layout = QFormLayout(syn_group)
        syn_layout.setSpacing(10)
        syn_layout.setContentsMargins(12, 20, 12, 12)

        self._syn_metric = QComboBox()
        self._syn_metric.addItems(["mattes", "meansquares", "CC", "demons"])
        syn_layout.addRow("度量:", self._syn_metric)

        self._syn_sampling = QSpinBox()
        self._syn_sampling.setRange(1, 1000)
        self._syn_sampling.setValue(20)
        syn_layout.addRow("直方图 bin 数:", self._syn_sampling)

        self._flow_sigma = QDoubleSpinBox()
        self._flow_sigma.setRange(0.01, 10.0)
        self._flow_sigma.setSingleStep(0.1)
        self._flow_sigma.setValue(0.6)
        syn_layout.addRow("流动场 sigma:", self._flow_sigma)

        self._total_sigma = QDoubleSpinBox()
        self._total_sigma.setRange(0.01, 10.0)
        self._total_sigma.setSingleStep(0.1)
        self._total_sigma.setValue(0.5)
        syn_layout.addRow("总 sigma:", self._total_sigma)

        self._reg_iter = QTextEdit()
        self._reg_iter.setMaximumHeight(42)
        self._reg_iter.setPlainText("400, 300, 200, 100")
        syn_layout.addRow("迭代次数:", self._reg_iter)

        self._mask_all = QCheckBox("所有阶段使用掩码")
        self._mask_all.setChecked(True)
        syn_layout.addRow(self._mask_all)

        layout.addWidget(syn_group)

        # ---- 执行 ----
        self._run_btn = QPushButton("执行配准")
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
        self._run_btn.clicked.connect(self._run)
        layout.addWidget(self._run_btn)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # ---- 日志 ----
        log_group = QGroupBox("执行日志")
        log_group.setStyleSheet(group_style)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(12, 20, 12, 12)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(150)
        log_layout.addWidget(self._log_text)
        layout.addWidget(log_group)

        layout.addStretch()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ---- 图像列表管理 ----
    def update_loaded_images(self, images):
        for combo in (self._fixed_combo, self._moving_combo, self._pet_combo, self._mask_combo):
            current_data = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("（未选择）", "")
            for img in images:
                label = f"{img.modality} - {img.name}"
                combo.addItem(label, img.path)
            idx = combo.findData(current_data)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def set_current_dir(self, directory: str):
        self._current_dir = directory

    def _auto_detect_files(self):
        import os
        directory = self._current_dir
        if not directory or not os.path.isdir(directory):
            self._log_text.append("请先在左侧文件浏览器中打开一个目录")
            return

        exts = {".nii", ".nii.gz", ".mha", ".mhd", ".nrrd", ".dcm"}
        files = []
        for f in os.listdir(directory):
            fl = f.lower()
            if any(fl.endswith(e) for e in exts):
                files.append(os.path.join(directory, f))

        if not files:
            self._log_text.append(f"目录中未找到医学影像文件: {directory}")
            return

        rtct_files = [f for f in files if "rtct" in os.path.basename(f).lower()]
        pet_files = [f for f in files if "pet" in os.path.basename(f).lower()]
        mask_files = [f for f in files if any(k in os.path.basename(f).lower() for k in ["mask", "roi", "seg"])]
        ct_files = [f for f in files if f not in rtct_files and f not in pet_files and f not in mask_files]

        def _set_combo(combo, path, label):
            if not path:
                return
            idx = combo.findData(path)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.addItem(os.path.basename(path), path)
                combo.setCurrentIndex(combo.count() - 1)
            self._log_text.append(f"  {label}: {os.path.basename(path)}")

        _set_combo(self._fixed_combo, rtct_files[0] if rtct_files else None, "固定图像(RTCT)")
        _set_combo(self._moving_combo, ct_files[0] if ct_files else None, "待配准图像(CT)")
        _set_combo(self._pet_combo, pet_files[0] if pet_files else None, "PET")
        _set_combo(self._mask_combo, mask_files[0] if mask_files else None, "掩码")

        if not rtct_files:
            self._log_text.append("提示: 未找到含 'RTCT' 的文件，请手动选择固定图像")
        if not ct_files:
            self._log_text.append("提示: 未找到 CT 文件，请手动选择待配准图像")

    def _on_fixed_changed(self, index):
        pass

    def _on_moving_changed(self, index):
        pass

    def _on_zseg_toggled(self, checked: bool):
        self._zseg_fixed.setVisible(checked)
        self._zseg_moving.setVisible(checked)

    def _browse_file(self, which: str):
        path, _ = QFileDialog.getOpenFileName(
            self, f"选择{'固定图像' if which == 'fixed' else '待配准图像' if which == 'moving' else 'PET' if which == 'pet' else '掩码'}",
            "", "NIfTI (*.nii *.nii.gz);;所有文件 (*)"
        )
        if not path:
            return
        import os
        name = os.path.basename(path)
        combo = {
            "fixed": self._fixed_combo,
            "moving": self._moving_combo,
            "pet": self._pet_combo,
            "mask": self._mask_combo,
        }[which]
        combo.addItem(name, path)
        combo.setCurrentIndex(combo.count() - 1)

    def _parse_int_list(self, text: str) -> list[int]:
        return [int(x.strip()) for x in text.split(",") if x.strip()]

    def _collect_params(self) -> dict:
        win_text = self._window_combo.currentText()
        if win_text.startswith("仅空气截断"):
            selected_window = None
        else:
            selected_window = win_text.split(" [")[0]

        return {
            "selected_window": selected_window,
            "use_z_segments": self._zseg_check.isChecked(),
            "z_segments_fixed": self._zseg_fixed.get_segments() if self._zseg_check.isChecked() else [],
            "z_segments_moving": self._zseg_moving.get_segments() if self._zseg_check.isChecked() else [],
            "aff_metric": self._aff_metric.currentText(),
            "aff_sampling": self._aff_sampling.value(),
            "aff_iterations": self._parse_int_list(self._aff_iter.toPlainText()),
            "aff_shrink_factors": self._parse_int_list(self._aff_shrink.toPlainText()),
            "aff_smoothing_sigmas": self._parse_int_list(self._aff_sigma.toPlainText()),
            "syn_metric": self._syn_metric.currentText(),
            "syn_sampling": self._syn_sampling.value(),
            "flow_sigma": self._flow_sigma.value(),
            "total_sigma": self._total_sigma.value(),
            "reg_iterations": self._parse_int_list(self._reg_iter.toPlainText()),
            "mask_all_stages": self._mask_all.isChecked(),
        }

    def _run(self):
        fixed = self._fixed_combo.currentData()
        moving = self._moving_combo.currentData()
        if not fixed or not moving:
            self._log_text.append("错误：请至少选择固定图像和待配准图像")
            return

        params = self._collect_params()
        self.log(f"开始配准  固定:{self._fixed_combo.currentText()}  移动:{self._moving_combo.currentText()}")
        self.registration_requested.emit(params)

    def log(self, msg: str):
        self._log_text.append(msg)

    def set_progress(self, value: int):
        self._progress.setVisible(True)
        self._progress.setValue(value)

    def get_paths(self) -> dict:
        return {
            "fixed": self._fixed_combo.currentData() or "",
            "moving": self._moving_combo.currentData() or "",
            "pet": self._pet_combo.currentData() or "",
            "mask": self._mask_combo.currentData() or "",
        }
