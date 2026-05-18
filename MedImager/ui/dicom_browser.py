import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTreeView,
    QFileSystemModel, QFileDialog, QLabel, QFrame, QHeaderView
)
from PySide6.QtCore import Signal, QDir

from ui.styles.tokens import Colors
from ui.styles.components import GlassPanel


class DicomBrowser(QWidget):
    """文件浏览器面板，支持浏览 DICOM/NIfTI/MHA/NRRD 文件。"""

    image_selected = Signal(str)
    directory_changed = Signal(str)

    SUPPORTED_EXTENSIONS = {
        ".dcm", ".nii", ".nii.gz", ".mha", ".mhd", ".nrrd",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # Wrap content in GlassPanel
        glass = GlassPanel(self, radius=10, opacity=0.06, border_opacity=0.06)
        glass_layout = QVBoxLayout(glass)
        glass_layout.setSpacing(6)
        glass_layout.setContentsMargins(8, 8, 8, 8)

        # Open button with glass styling
        self._open_btn = QPushButton("打开目录...")
        self._open_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.06);
                color: {Colors.TEXT_BODY};
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.10);
                border-color: rgba(255, 255, 255, 0.18);
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton:pressed {{
                background: {Colors.ACCENT};
                border-color: {Colors.ACCENT};
            }}
        """)
        self._open_btn.clicked.connect(self._open_directory)
        glass_layout.addWidget(self._open_btn)

        # Tree view
        self._tree = QTreeView()
        self._model = QFileSystemModel()
        self._model.setRootPath("")
        self._tree.setModel(self._model)
        self._tree.setAnimated(True)
        self._tree.setIndentation(20)
        self._tree.setHeaderHidden(False)
        self._tree.doubleClicked.connect(self._on_double_click)

        # Hide unnecessary columns (size, type, date) - only show name
        self._tree.setColumnHidden(1, True)
        self._tree.setColumnHidden(2, True)
        self._tree.setColumnHidden(3, True)
        self._tree.header().setStretchLastSection(False)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        glass_layout.addWidget(self._tree, stretch=1)

        # Info label at bottom
        info_frame = GlassPanel(glass, radius=6, opacity=0.08, border_opacity=0.06)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 6, 8, 6)

        self._info_label = QLabel("双击文件加载图像")
        self._info_label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 11px;
            background: transparent;
            border: none;
        """)
        info_layout.addWidget(self._info_label)
        glass_layout.addWidget(info_frame)

        layout.addWidget(glass)

    def get_current_dir(self) -> str:
        idx = self._tree.rootIndex()
        if idx.isValid():
            return self._model.filePath(idx)
        return ""

    def list_files(self, extensions: set[str] | None = None) -> list[str]:
        cur_dir = self.get_current_dir()
        if not cur_dir or not os.path.isdir(cur_dir):
            return []
        if extensions is None:
            extensions = self.SUPPORTED_EXTENSIONS
        result = []
        for f in sorted(os.listdir(cur_dir)):
            full = os.path.join(cur_dir, f)
            if os.path.isfile(full):
                ext = f.lower()
                if any(ext.endswith(e) for e in extensions):
                    result.append(full)
            elif os.path.isdir(full):
                result.append(full + "/")
        return result

    def _open_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择图像目录")
        if dir_path:
            idx = self._model.index(dir_path)
            self._tree.setRootIndex(idx)
            self._info_label.setText(f"当前目录: {os.path.basename(dir_path)}")
            self.directory_changed.emit(dir_path)

    def _on_double_click(self, index):
        path = self._model.filePath(index)
        if os.path.isfile(path):
            ext = ""
            if path.endswith(".nii.gz"):
                ext = ".nii.gz"
            else:
                _, ext = os.path.splitext(path)
            if ext.lower() in self.SUPPORTED_EXTENSIONS:
                self.image_selected.emit(path)
