import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider, QGridLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from core.image_io import load_image
from core.image_volume import ImageVolume
from ui.styles.tokens import Colors, Fonts
from ui.styles.components import GlassLabel, GlassPanel


COLORMAPS = {
    "灰度": None,
    "热力 (Hot)": pg.ColorMap(pos=[0.0, 0.33, 0.66, 1.0], color=[(0, 0, 0), (220, 0, 0), (255, 220, 0), (255, 255, 255)]),
    "Viridis": pg.ColorMap(pos=[0.0, 0.25, 0.5, 0.75, 1.0], color=[(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)]),
    "Inferno": pg.ColorMap(pos=[0.0, 0.25, 0.5, 0.75, 1.0], color=[(0, 0, 4), (156, 50, 108), (240, 135, 39), (252, 230, 99), (252, 253, 191)]),
    "Jet": pg.ColorMap(pos=[0.0, 0.25, 0.5, 0.75, 1.0], color=[(0, 0, 143), (0, 255, 255), (255, 255, 0), (255, 0, 0), (128, 0, 0)]),
}


class _PlaneView(QWidget):
    """单个解剖面查看子窗口。"""

    slice_changed = Signal()

    def __init__(self, plane_name: str, plane_index: int, parent=None):
        super().__init__(parent)
        self._plane_name = plane_name
        self._plane_index = plane_index
        self._volume = None
        self._ww = 400
        self._wl = 40
        self._auto = False
        self._cmap = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Floating glass title label (positioned absolutely over the image)
        self._glass_title = GlassLabel(plane_name, self, radius=6, opacity=0.08)
        self._glass_title.setFixedHeight(28)
        self._glass_title.setMinimumWidth(120)
        self._glass_title.move(8, 8)
        self._glass_title.raise_()

        # Image viewport
        self._glw = pg.GraphicsLayoutWidget()
        self._glw.setBackground("#000000")
        self._glw.setStyleSheet("border: none;")
        self._vb = self._glw.addViewBox(row=0, col=0)
        self._img = pg.ImageItem()
        self._vb.addItem(self._img)
        self._vb.setAspectLocked(False)
        self._vb.setDefaultPadding(0)
        self._vb.enableAutoRange()
        root.addWidget(self._glw, stretch=1)

        # Bottom bar with slice info and slider
        bottom_frame = QFrame()
        bottom_frame.setFixedHeight(48)
        bottom_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.03);
                border-top: 1px solid {Colors.BORDER};
            }}
        """)
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(10, 4, 10, 4)
        bottom_layout.setSpacing(8)

        self._slice_label = QLabel("0 / 0")
        self._slice_label.setAlignment(Qt.AlignCenter)
        self._slice_label.setFixedWidth(70)
        self._slice_label.setStyleSheet(f"""
            font-size: 11px;
            color: {Colors.TEXT_MUTED};
            font-family: {Fonts.MONO};
            background: transparent;
            border: none;
        """)
        bottom_layout.addWidget(self._slice_label)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.valueChanged.connect(self._on_slider)
        bottom_layout.addWidget(self._slider, stretch=1)

        root.addWidget(bottom_frame)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._glass_title.move(8, 8)
        self._glass_title.raise_()

    def set_volume(self, vol: ImageVolume):
        self._volume = vol
        axis = 2 - self._plane_index
        n = vol.data.shape[axis]
        self._slider.blockSignals(True)
        self._slider.setRange(0, max(n - 1, 0))
        self._slider.setValue(n // 2)
        self._slider.blockSignals(False)

        sx, sy, sz = vol.spacing
        if self._plane_index == 0:
            ratio = sx / sy
        elif self._plane_index == 1:
            ratio = sx / sz
        else:
            ratio = sy / sz
        self._vb.setAspectLocked(True, ratio=ratio)

        self._display()

    def set_wl(self, ww, wl, auto=False):
        self._ww, self._wl, self._auto = ww, wl, auto
        self._display()

    def set_cmap(self, cmap):
        self._cmap = cmap
        if cmap:
            self._img.setLookupTable(cmap.getLookupTable(0, 1, 256))
        else:
            self._img.setLookupTable(None)
        self._display()

    def set_slice(self, idx):
        self._slider.setValue(idx)

    def _on_slider(self, _):
        self._display()
        self.slice_changed.emit()

    def _display(self):
        if self._volume is None:
            return

        data = self._volume.data
        idx = self._slider.value()
        axis = 2 - self._plane_index

        if axis == 2:
            sl = data[:, :, idx]
        elif axis == 1:
            sl = data[:, idx, :]
        else:
            sl = data[idx, :, :]

        sl = sl.astype(np.float32)

        if self._auto:
            lo, hi = sl.min(), sl.max()
            sl = (sl - lo) / (hi - lo) if hi > lo else np.zeros_like(sl)
        else:
            sl = np.clip((sl - self._wl + self._ww / 2) / self._ww, 0, 1)

        self._img.setImage(sl)

        n = data.shape[axis]
        self._slice_label.setText(f"{idx + 1} / {n}")
        self._glass_title.setText(f"{self._plane_name}  [{idx}]")


class ImageViewer(QWidget):
    """三轴面同步显示。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._volume = None
        self._ww = 400
        self._wl = 40
        self._is_pet = False

        self.setStyleSheet(f"background-color: #000000;")

        g = QGridLayout(self)
        g.setContentsMargins(2, 2, 2, 2)
        g.setSpacing(2)

        self._ax = _PlaneView("轴状面 Axial", 0)
        self._cor = _PlaneView("冠状面 Coronal", 1)
        self._sag = _PlaneView("矢状面 Sagittal", 2)

        g.addWidget(self._ax, 0, 0)
        g.addWidget(self._cor, 0, 1)
        g.addWidget(self._sag, 1, 0)

        # Info panel with glass card styling
        info_frame = GlassPanel(self, radius=12, opacity=0.08, border_opacity=0.06)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(8)

        # Welcome icon/title
        welcome_label = QLabel("MedImager")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {Colors.ACCENT};
            background: transparent;
            border: none;
        """)
        info_layout.addWidget(welcome_label)

        self._info = QLabel("请打开一个医学图像文件")
        self._info.setAlignment(Qt.AlignCenter)
        self._info.setWordWrap(True)
        self._info.setStyleSheet(f"""
            font-size: 13px;
            color: {Colors.TEXT_MUTED};
            background: transparent;
            border: none;
            line-height: 1.6;
        """)
        info_layout.addWidget(self._info)

        g.addWidget(info_frame, 1, 1)

    def load_image(self, path: str):
        vol = load_image(path)
        self.set_volume(vol)

    def set_volume(self, vol: ImageVolume):
        self._volume = vol
        mod = vol.get_modality().upper()
        self._is_pet = (mod == "PT" or "PET" in mod or "pet" in vol.file_path.lower())

        if self._is_pet:
            for v in (self._ax, self._cor, self._sag):
                v._auto = True
            self.set_colormap(COLORMAPS["热力 (Hot)"])
        else:
            for v in (self._ax, self._cor, self._sag):
                v._auto = False
            self.set_colormap(None)
            self.set_window_level(self._ww, self._wl)

        for v in (self._ax, self._cor, self._sag):
            v.set_volume(vol)

        sp = vol.spacing
        self._info.setText(
            f"形状: {vol.shape}\n"
            f"间距: {sp[0]:.2f} x {sp[1]:.2f} x {sp[2]:.2f}\n"
            f"模态: {vol.get_modality()}\n"
            f"{'PET' if self._is_pet else 'CT / MRI'}"
        )

    def set_window_level(self, w, l):
        self._ww, self._wl = w, l
        for v in (self._ax, self._cor, self._sag):
            v.set_wl(w, l)

    def set_colormap(self, cm):
        for v in (self._ax, self._cor, self._sag):
            v.set_cmap(cm)

    def set_view_plane(self, _): pass
    def get_volume(self): return self._volume

    @property
    def is_pet(self): return self._is_pet
    @property
    def axial_view(self):    return self._ax
    @property
    def coronal_view(self):  return self._cor
    @property
    def sagittal_view(self): return self._sag
