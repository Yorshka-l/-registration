from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QFileDialog, QToolBar,
    QLabel, QSlider, QComboBox, QWidget, QHBoxLayout,
    QStatusBar, QMessageBox, QMenuBar, QFrame, QVBoxLayout
)
from PySide6.QtCore import Qt, QSize, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QFont
import threading

from ui.image_viewer import ImageViewer
from ui.dicom_browser import DicomBrowser
from ui.registration_panel import RegistrationPanel
from ui.segmentation_panel import SegmentationPanel
from ui.agent_panel import AgentPanel
from ui.styles.tokens import Colors, Fonts
from ui.styles.components import GlassPanel


class MainWindow(QMainWindow):
    def __init__(self, state, image_svc, reg_svc, seg_svc, agent_svc, workers):
        super().__init__()
        self.setWindowTitle("MedImager - 医学图像处理平台")
        self.setMinimumSize(1400, 900)

        self._state = state
        self._image_svc = image_svc
        self._reg_svc = reg_svc
        self._seg_svc = seg_svc
        self._agent_svc = agent_svc
        self._workers = workers

        self._image_viewer = ImageViewer()
        self.setCentralWidget(self._image_viewer)

        self._init_docks()
        self._init_menu_bar()
        self._init_toolbar()
        self._init_status_bar()
        self._connect_signals()
        self._register_agent_tools()

    def _connect_signals(self):
        self._state.image_loaded.connect(self._on_image_loaded)
        self._state.status_changed.connect(self._on_status_changed)
        self._state.registration_started.connect(
            lambda: self._status_bar.showMessage("配准执行中..."))
        self._state.registration_finished.connect(self._on_registration_done)
        self._state.registration_failed.connect(self._on_registration_error)
        self._state.registration_log.connect(self._registration_panel.log)
        self._agent_panel.message_sent.connect(self._on_agent_message)
        self._agent_panel._clear_btn.clicked.connect(self._on_agent_clear)
        self._agent_panel._settings_btn.clicked.connect(self._reset_agent)

    def _init_docks(self):
        dock_style = f"""
            QDockWidget {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: 600;
                font-size: 13px;
                background-color: #080c14;
                border: none;
            }}
            QDockWidget::title {{
                background-color: rgba(255, 255, 255, 0.06);
                padding: 10px 16px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.12);
                border-left: 3px solid {Colors.ACCENT};
                text-align: left;
            }}
            QDockWidget > QWidget {{
                background-color: #0a0e16;
                border: none;
            }}
        """

        # Left: file browser
        self._browser_dock = QDockWidget("文件浏览器", self)
        self._browser_dock.setObjectName("browser_dock")
        self._browser_dock.setStyleSheet(dock_style)
        self._browser = DicomBrowser()
        self._browser.image_selected.connect(self._on_image_selected)
        self._browser_dock.setWidget(self._browser)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._browser_dock)

        # Right: registration panel
        self._registration_dock = QDockWidget("配准", self)
        self._registration_dock.setObjectName("registration_dock")
        self._registration_dock.setStyleSheet(dock_style)
        self._registration_panel = RegistrationPanel()
        self._registration_panel.registration_requested.connect(self._on_registration_requested)
        self._browser.directory_changed.connect(self._registration_panel.set_current_dir)
        self._registration_dock.setWidget(self._registration_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self._registration_dock)
        self._registration_dock.hide()

        # Right: segmentation panel
        self._segmentation_dock = QDockWidget("分割", self)
        self._segmentation_dock.setObjectName("segmentation_dock")
        self._segmentation_dock.setStyleSheet(dock_style)
        self._segmentation_panel = SegmentationPanel()
        self._segmentation_dock.setWidget(self._segmentation_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self._segmentation_dock)
        self._segmentation_dock.hide()

        # Bottom: agent panel
        self._agent_dock = QDockWidget("AI Agent", self)
        self._agent_dock.setObjectName("agent_dock")
        self._agent_dock.setStyleSheet(dock_style)
        self._agent_panel = AgentPanel()
        self._agent_dock.setWidget(self._agent_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self._agent_dock)

    def _init_menu_bar(self):
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)

        file_menu = menubar.addMenu("文件(&F)")
        open_action = QAction("打开图像...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        open_dir_action = QAction("打开 DICOM 目录...", self)
        open_dir_action.triggered.connect(self._open_dicom_dir)
        file_menu.addAction(open_dir_action)

        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("视图(&V)")
        view_menu.addAction(self._browser_dock.toggleViewAction())
        view_menu.addAction(self._registration_dock.toggleViewAction())
        view_menu.addAction(self._segmentation_dock.toggleViewAction())
        view_menu.addAction(self._agent_dock.toggleViewAction())

        tools_menu = menubar.addMenu("工具(&T)")
        reg_action = QAction("配准", self)
        reg_action.triggered.connect(lambda: self._registration_dock.setVisible(True))
        tools_menu.addAction(reg_action)

        seg_action = QAction("图像分割", self)
        seg_action.triggered.connect(lambda: self._segmentation_dock.setVisible(True))
        tools_menu.addAction(seg_action)

        help_menu = menubar.addMenu("帮助(&H)")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Toolbar label style
        label_style = f"""
            font-size: 11px;
            color: {Colors.TEXT_MUTED};
            font-weight: 500;
            padding: 0 2px;
            background: transparent;
            border: none;
            letter-spacing: 0.3px;
        """

        # Value label style
        value_style = f"""
            font-size: 12px;
            color: {Colors.ACCENT};
            font-weight: 600;
            font-family: {Fonts.MONO};
            padding: 0 4px;
            background: transparent;
            border: none;
        """

        # Window width
        ww_label = QLabel("窗宽")
        ww_label.setStyleSheet(label_style)
        toolbar.addWidget(ww_label)

        self._ww_slider = QSlider(Qt.Horizontal)
        self._ww_slider.setRange(1, 4096)
        self._ww_slider.setValue(400)
        self._ww_slider.setFixedWidth(140)
        self._ww_slider.valueChanged.connect(self._on_window_level_changed)
        toolbar.addWidget(self._ww_slider)

        self._ww_label = QLabel("400")
        self._ww_label.setStyleSheet(value_style)
        self._ww_label.setFixedWidth(44)
        toolbar.addWidget(self._ww_label)

        # Separator frame
        sep_style = f"color: rgba(255,255,255,0.06); background: rgba(255,255,255,0.06); max-width: 1px; margin: 4px 6px;"
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet(sep_style)
        toolbar.addWidget(sep1)

        # Window level
        wl_label = QLabel("窗位")
        wl_label.setStyleSheet(label_style)
        toolbar.addWidget(wl_label)

        self._wl_slider = QSlider(Qt.Horizontal)
        self._wl_slider.setRange(-1024, 3072)
        self._wl_slider.setValue(40)
        self._wl_slider.setFixedWidth(140)
        self._wl_slider.valueChanged.connect(self._on_window_level_changed)
        toolbar.addWidget(self._wl_slider)

        self._wl_label = QLabel("40")
        self._wl_label.setStyleSheet(value_style)
        self._wl_label.setFixedWidth(44)
        toolbar.addWidget(self._wl_label)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet(sep_style)
        toolbar.addWidget(sep2)

        # Preset combo
        preset_label = QLabel("预设")
        preset_label.setStyleSheet(label_style)
        toolbar.addWidget(preset_label)

        self._preset_combo = QComboBox()
        self._preset_combo.setFixedWidth(180)
        self._preset_combo.addItems([
            "自定义",
            "软组织 (W:400 L:40)",
            "肺 (W:1500 L:-600)",
            "骨 (W:2000 L:300)",
            "脑 (W:80 L:40)",
            "肝脏 (W:150 L:30)",
            "PET SUV 0-5",
            "PET SUV 0-10",
            "PET SUV 0-20",
        ])
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        toolbar.addWidget(self._preset_combo)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.VLine)
        sep3.setStyleSheet(sep_style)
        toolbar.addWidget(sep3)

        # Colormap combo
        cmap_label = QLabel("色表")
        cmap_label.setStyleSheet(label_style)
        toolbar.addWidget(cmap_label)

        self._cmap_combo = QComboBox()
        self._cmap_combo.setFixedWidth(120)
        from ui.image_viewer import COLORMAPS
        self._cmap_combo.addItems(list(COLORMAPS.keys()))
        self._cmap_combo.currentIndexChanged.connect(self._on_colormap_changed)
        toolbar.addWidget(self._cmap_combo)

    def _init_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("就绪")

        # Status indicator
        self._status_indicator = QLabel("●")
        self._status_indicator.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 10px; padding: 0 4px; background: transparent;")
        self._status_bar.addPermanentWidget(self._status_indicator)

        self._pos_label = QLabel("")
        self._pos_label.setStyleSheet(f"""
            font-family: {Fonts.MONO};
            font-size: 11px;
            color: {Colors.TEXT_MUTED};
            padding: 0 4px;
            background: transparent;
        """)
        self._status_bar.addPermanentWidget(self._pos_label)

    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开医学图像", "",
            "所有支持格式 (*.dcm *.nii *.nii.gz *.mha *.mhd *.nrrd);;"
            "DICOM (*.dcm);;NIfTI (*.nii *.nii.gz);;MetaImage (*.mha *.mhd);;"
            "NRRD (*.nrrd);;所有文件 (*)",
        )
        if file_path:
            self._load_image(file_path)

    def _open_dicom_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择 DICOM 目录")
        if dir_path:
            self._load_image(dir_path)

    def _load_image(self, path: str):
        try:
            vol, info = self._image_svc.load(path)
            self._image_viewer.set_volume(vol)
            self._state.set_image(info)
            self._registration_panel.update_loaded_images(self._state.image.loaded_images)
            self._state.status_changed.emit("ready", f"已加载: {info.name}")
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"无法加载图像:\n{e}")
            self._state.status_changed.emit("error", str(e))

    def _on_image_selected(self, path: str):
        self._load_image(path)

    def _on_image_loaded(self, info):
        self._status_bar.showMessage(
            f"已加载: {info.name}  |  形状: {info.shape}  |  模态: {info.modality}")

    def _on_status_changed(self, state, message):
        colors = {"ready": Colors.SUCCESS, "busy": Colors.WARNING, "error": Colors.ERROR}
        color = colors.get(state, Colors.TEXT_MUTED)
        self._status_indicator.setStyleSheet(
            f"color: {color}; font-size: 10px; padding: 0 4px; background: transparent;")

    def _on_window_level_changed(self):
        ww = self._ww_slider.value()
        wl = self._wl_slider.value()
        self._ww_label.setText(str(ww))
        self._wl_label.setText(str(wl))
        self._image_viewer.set_window_level(ww, wl)
        self._preset_combo.setCurrentIndex(0)

    def _on_preset_changed(self, index: int):
        presets = {
            1: (400, 40), 2: (1500, -600), 3: (2000, 300), 4: (80, 40), 5: (150, 30),
            6: (5, 2.5), 7: (10, 5), 8: (20, 10),
        }
        if index in presets:
            ww, wl = presets[index]
            self._ww_slider.setValue(ww)
            self._wl_slider.setValue(wl)

    def _on_colormap_changed(self, index: int):
        from ui.image_viewer import COLORMAPS
        name = self._cmap_combo.currentText()
        cmap = COLORMAPS.get(name)
        self._image_viewer.set_colormap(cmap)

    def _show_about(self):
        QMessageBox.about(
            self, "关于 MedImager",
            "MedImager v0.1.0\n\n"
            "医学图像处理平台\n"
            "支持 DICOM / NIfTI / MHA / NRRD 格式\n"
            "支持三轴面同步查看、配准、分割及 AI Agent 对话\n\n"
            "制作者: Yorshka",
        )

    # ------------------------------------------------------------------ #
    #  Registration
    # ------------------------------------------------------------------ #
    def _on_registration_requested(self, params: dict):
        paths = self._registration_panel.get_paths()
        if not paths["fixed"] or not paths["moving"]:
            self._registration_panel.log("错误：请先选择图像文件")
            return

        self._state.registration_started.emit()
        self._state.status_changed.emit("busy", "配准执行中...")

        worker = self._workers.start(
            "registration",
            self._reg_svc.run_synra,
            paths["fixed"], paths["moving"],
            pet=paths.get("pet"), mask=paths.get("mask"),
            params=params,
        )
        worker.finished.connect(self._on_registration_done)
        worker.error.connect(self._on_registration_error)
        worker.log.connect(self._registration_panel.log)

    def _on_registration_done(self, result: dict):
        self._registration_panel.set_progress(100)
        self._registration_panel.log("配准完成！")
        ct = result.get("ct")
        if ct and ct.file_path:
            self._load_image(ct.file_path)
        self._state.status_changed.emit("ready", "配准完成")

    def _on_registration_error(self, error: str):
        self._registration_panel.log(f"配准失败: {error}")
        self._state.status_changed.emit("error", "配准失败")

    def _on_multimodal_done(self, result: dict):
        self._registration_panel.log("多模态配准完成！")
        moving_final = result.get("moving_final")
        if moving_final and moving_final.file_path:
            self._load_image(moving_final.file_path)
        self._state.status_changed.emit("ready", "多模态配准完成")

    def _on_multimodal_error(self, error: str):
        self._registration_panel.log(f"多模态配准失败: {error}")
        self._state.status_changed.emit("error", "多模态配准失败")

    def _agent_triggered_registration(self):
        """由 Agent 触发的配准，在主线程中执行。"""
        try:
            params = self._registration_panel._collect_params()
            self._on_registration_requested(params)
        except Exception as e:
            self._registration_panel.log(f"配准启动失败: {e}")
            self._state.status_changed.emit("error", "配准启动失败")

    # ------------------------------------------------------------------ #
    #  Agent integration
    # ------------------------------------------------------------------ #
    def _on_agent_message(self, text: str):
        self._agent_panel.append_system_message("思考中...")
        self._agent_panel._send_btn.setEnabled(False)
        worker = self._workers.start("agent", self._agent_svc.chat, text)
        worker.finished.connect(self._on_agent_reply)
        worker.error.connect(self._on_agent_error)

    def _on_agent_reply(self, reply: str):
        self._agent_panel._send_btn.setEnabled(True)
        self._agent_panel.append_assistant_message(reply)

    def _on_agent_error(self, error: str):
        self._agent_panel._send_btn.setEnabled(True)
        self._agent_panel.append_system_message(f"错误: {error}")

    def _on_agent_clear(self):
        self._agent_svc.clear_history()

    def _reset_agent(self):
        self._agent_svc.reset()

    def _run_tool_on_main(self, func, *args, **kwargs):
        """在主线程执行工具函数并同步返回结果（供 Agent 后台线程调用）。"""
        result_box = [None]
        event = threading.Event()

        def wrapper():
            try:
                result_box[0] = func(*args, **kwargs)
            except Exception as e:
                result_box[0] = f"执行失败: {e}"
            finally:
                event.set()

        QTimer.singleShot(0, wrapper)
        event.wait(timeout=30)
        return result_box[0] if result_box[0] is not None else "执行超时（30秒）"

    def _register_agent_tools(self):
        reg = self._agent_svc.tools
        main = self._run_tool_on_main

        reg.register("load_image", lambda a: main(self._load_image, a["path"]))
        reg.register("set_window_level", lambda a: main(self._set_window_level, a["window_width"], a["window_level"]))
        reg.register("set_slice", lambda a: main(self._image_viewer.axial_view.set_slice, a["index"]))
        reg.register("get_image_info", lambda a: main(self._tool_get_image_info))
        reg.register("apply_preset", lambda a: main(self._tool_apply_preset, a["preset"]))
        reg.register("set_reg_param", lambda a: main(self._tool_set_reg_param, a))
        reg.register("set_reg_files", lambda a: main(self._tool_set_reg_files, a))
        reg.register("run_registration", lambda a: main(self._tool_run_registration))
        reg.register("list_loaded_images", lambda a: main(self._tool_list_loaded_images))
        reg.register("get_current_directory", lambda a: main(self._browser.get_current_dir))
        reg.register("list_directory_files", lambda a: main(self._browser.list_files))
        reg.register("run_multimodal_registration", lambda a: main(self._tool_run_multimodal, a))

    # ------------------------------------------------------------------ #
    #  Agent tool helpers
    # ------------------------------------------------------------------ #
    def _set_window_level(self, ww, wl):
        self._ww_slider.setValue(ww)
        self._wl_slider.setValue(wl)

    def _tool_get_image_info(self):
        vol = self._image_viewer.get_volume()
        if vol is None:
            return "当前未加载任何图像"
        return f"形状: {vol.shape}, 间距: {vol.spacing}, 模态: {vol.get_modality()}, 患者: {vol.get_patient_name()}"

    def _tool_apply_preset(self, preset):
        from agent.tools import WINDOW_PRESETS
        if preset in WINDOW_PRESETS:
            ww, wl = WINDOW_PRESETS[preset]
            self._ww_slider.setValue(ww)
            self._wl_slider.setValue(wl)
            return f"已应用预设 {preset}: W:{ww} L:{wl}"
        return f"未知预设: {preset}"

    def _tool_set_reg_param(self, args):
        panel = self._registration_panel
        self._registration_dock.setVisible(True)
        changed = []
        if "selected_window" in args:
            from core.registration import WINDOW_SETTINGS
            name = args["selected_window"]
            if name in WINDOW_SETTINGS:
                for i in range(panel._window_combo.count()):
                    if panel._window_combo.itemText(i).startswith(name):
                        panel._window_combo.setCurrentIndex(i)
                        break
                changed.append(f"窗位={name}")
        if "aff_metric" in args:
            idx = panel._aff_metric.findText(args["aff_metric"])
            if idx >= 0:
                panel._aff_metric.setCurrentIndex(idx)
                changed.append(f"aff_metric={args['aff_metric']}")
        if "aff_sampling" in args:
            panel._aff_sampling.setValue(args["aff_sampling"])
            changed.append(f"aff_sampling={args['aff_sampling']}")
        if "aff_iterations" in args:
            panel._aff_iter.setPlainText(", ".join(str(x) for x in args["aff_iterations"]))
            changed.append("aff_iterations")
        if "aff_shrink_factors" in args:
            panel._aff_shrink.setPlainText(", ".join(str(x) for x in args["aff_shrink_factors"]))
            changed.append("aff_shrink")
        if "aff_smoothing_sigmas" in args:
            panel._aff_sigma.setPlainText(", ".join(str(x) for x in args["aff_smoothing_sigmas"]))
            changed.append("aff_sigma")
        if "syn_metric" in args:
            idx = panel._syn_metric.findText(args["syn_metric"])
            if idx >= 0:
                panel._syn_metric.setCurrentIndex(idx)
                changed.append(f"syn_metric={args['syn_metric']}")
        if "syn_sampling" in args:
            panel._syn_sampling.setValue(args["syn_sampling"])
            changed.append("syn_sampling")
        if "flow_sigma" in args:
            panel._flow_sigma.setValue(args["flow_sigma"])
            changed.append("flow_sigma")
        if "total_sigma" in args:
            panel._total_sigma.setValue(args["total_sigma"])
            changed.append("total_sigma")
        if "reg_iterations" in args:
            panel._reg_iter.setPlainText(", ".join(str(x) for x in args["reg_iterations"]))
            changed.append("reg_iterations")
        return f"已更新配准参数: {', '.join(changed)}" if changed else "未检测到有效参数"

    def _tool_set_reg_files(self, args):
        import os
        panel = self._registration_panel
        self._registration_dock.setVisible(True)
        changed = []
        for key, combo in [("fixed", panel._fixed_combo), ("moving", panel._moving_combo),
                           ("pet", panel._pet_combo), ("mask", panel._mask_combo)]:
            if key in args:
                path = args[key]
                idx = combo.findData(path)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                else:
                    combo.addItem(os.path.basename(path), path)
                    combo.setCurrentIndex(combo.count() - 1)
                changed.append(f"{key}={os.path.basename(path)}")
        return f"已设置配准文件: {', '.join(changed)}" if changed else "未指定文件"

    def _tool_run_registration(self):
        paths = self._registration_panel.get_paths()
        if not paths["fixed"] or not paths["moving"]:
            return "错误：请先用 set_reg_files 设置固定图像和待配准图像路径"
        self._agent_triggered_registration()
        return "配准已启动，请等待完成"

    def _tool_list_loaded_images(self):
        images = self._state.image.loaded_images
        if not images:
            return "当前没有已加载的图像"
        lines = []
        for i, img in enumerate(images):
            lines.append(f"{i+1}. [{img.modality}] {img.name}  路径: {img.path}")
        return "\n".join(lines)

    def _tool_run_multimodal(self, args):
        import os
        mode = args.get("mode")
        mri_path = args.get("mri_path", "")
        pet_path = args.get("pet_path", "")

        if not mode or mode not in ("mri_to_pet", "pet_to_mri"):
            return "错误：mode 必须为 'mri_to_pet' 或 'pet_to_mri'"
        if not mri_path or not os.path.isfile(mri_path):
            return f"错误：MRI 文件不存在: {mri_path}"
        if not pet_path or not os.path.isfile(pet_path):
            return f"错误：PET 文件不存在: {pet_path}"

        self._state.status_changed.emit("busy", "多模态配准执行中...")
        worker = self._workers.start(
            "multimodal",
            self._reg_svc.run_multimodal,
            mode, mri_path, pet_path,
        )
        worker.finished.connect(self._on_multimodal_done)
        worker.error.connect(self._on_multimodal_error)
        mode_cn = "MRI → PET" if mode == "mri_to_pet" else "PET → MRI"
        return f"多模态配准已启动 ({mode_cn})，请等待完成"
