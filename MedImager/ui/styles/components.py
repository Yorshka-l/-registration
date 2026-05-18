"""组件样式生成器 — 返回 QSS 字符串。"""

import ctypes
import ctypes.wintypes
from PySide6.QtWidgets import QWidget, QGraphicsBlurEffect, QVBoxLayout
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen, QPainterPath, QPixmap, QImage

from ui.styles.tokens import Colors, Fonts, Spacing, Radius


def _apply_dwm_blur(hwnd, enable=True):
    """Apply Windows DWM blur behind window effect."""
    try:
        dwmapi = ctypes.windll.dwmapi
        class DWM_BLURBEHIND(ctypes.Structure):
            _fields_ = [
                ("dwFlags", ctypes.wintypes.DWORD),
                ("fEnable", ctypes.wintypes.BOOL),
                ("hRgn", ctypes.wintypes.HRGN),
                ("fTransitionOnMaximized", ctypes.wintypes.BOOL),
            ]
        bb = DWM_BLURBEHIND()
        bb.dwFlags = 0x1  # DWM_BB_ENABLE
        bb.fEnable = enable
        bb.hRgn = 0
        bb.fTransitionOnMaximized = False
        dwmapi.DwmEnableBlurBehindWindow(hwnd, ctypes.byref(bb))
        return True
    except Exception:
        return False


class GlassPanel(QWidget):
    """Semi-transparent glass panel with real blur effect and rounded corners.

    On Windows, applies DWM blur behind the widget for true frosted glass.
    Falls back to gradient + glow effect on other platforms.
    """

    def __init__(self, parent=None, radius=12, opacity=0.10, border_opacity=0.06):
        super().__init__(parent)
        self._radius = radius
        self._opacity = opacity
        self._border_opacity = border_opacity
        self._blur_enabled = False
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

    def showEvent(self, event):
        super().showEvent(event)
        # Try DWM blur on Windows for top-level windows
        if not self._blur_enabled:
            win_id = self.winId()
            self._blur_enabled = _apply_dwm_blur(int(win_id), True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        # Clip to rounded rectangle
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)
        p.setClipPath(path)

        # Layer 1: Solid dark base
        p.fillRect(rect, QColor(8, 12, 20, 230))

        # Layer 2: Semi-transparent white overlay (the "frost" layer)
        frost = QColor(255, 255, 255, int(255 * self._opacity))
        p.fillRect(rect, frost)

        # Layer 3: Top-to-bottom gradient (lighter at top for depth)
        grad = QLinearGradient(0, 0, 0, rect.height())
        grad.setColorAt(0.0, QColor(255, 255, 255, int(255 * self._opacity * 0.8)))
        grad.setColorAt(0.5, QColor(255, 255, 255, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 20))
        p.fillRect(rect, grad)

        # Layer 4: Inner glow (brighter top edge)
        inner_glow = QLinearGradient(0, 0, 0, 4)
        inner_glow.setColorAt(0.0, QColor(255, 255, 255, int(255 * self._border_opacity * 0.5)))
        inner_glow.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(QRect(rect.x(), rect.y(), rect.width(), 4), inner_glow)

        # Layer 5: Glowing border
        pen = QPen(QColor(255, 255, 255, int(255 * self._border_opacity)))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, self._radius, self._radius)

        p.end()


class GlassLabel(QWidget):
    """Floating glass label with visible glass effect.

    Renders a frosted-glass-style label that floats over content.
    Use move() to position it absolutely within its parent.
    """

    def __init__(self, text="", parent=None, radius=6, opacity=0.08):
        super().__init__(parent)
        self._text = text
        self._radius = radius
        self._opacity = opacity
        self._text_color = QColor("#e2e8f0")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def setText(self, text):
        self._text = text
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QFont
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        # Clip to rounded rectangle
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)
        p.setClipPath(path)

        # Dark base
        p.fillRect(rect, QColor(8, 12, 20, 200))

        # Frost overlay
        frost = QColor(255, 255, 255, int(255 * self._opacity))
        p.fillRect(rect, frost)

        # Top gradient
        grad = QLinearGradient(0, 0, 0, rect.height())
        grad.setColorAt(0.0, QColor(255, 255, 255, int(255 * self._opacity * 0.6)))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(rect, grad)

        # Glowing border
        pen = QPen(QColor(255, 255, 255, int(255 * 0.08)))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, self._radius, self._radius)

        # Text with shadow
        font = QFont("Segoe UI", 11)
        font.setWeight(QFont.DemiBold)
        p.setFont(font)
        # Text shadow
        p.setPen(QColor(0, 0, 0, 80))
        p.drawText(rect.adjusted(1, 1, 1, 1), Qt.AlignCenter, self._text)
        # Actual text
        p.setPen(self._text_color)
        p.drawText(rect, Qt.AlignCenter, self._text)

        p.end()


def dock_title() -> str:
    return f"""
        QDockWidget {{
            color: {Colors.TEXT_PRIMARY};
            font-weight: 600;
            font-size: 13px;
            background-color: {Colors.BG_BASE};
            border: none;
        }}
        QDockWidget::title {{
            background-color: rgba(255, 255, 255, 0.03);
            padding: 10px 16px;
            border-bottom: 1px solid {Colors.BORDER};
            border-left: 3px solid {Colors.ACCENT};
            text-align: left;
        }}
    """


def primary_button() -> str:
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.ACCENT_DIM}, stop:1 {Colors.ACCENT});
            color: {Colors.WHITE};
            border: none;
            border-radius: {Radius.LG};
            padding: 12px 24px;
            font-size: 14px;
            font-weight: {Fonts.WEIGHT_SEMIBOLD};
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.ACCENT}, stop:1 {Colors.ACCENT_LIGHT});
        }}
        QPushButton:pressed {{
            background: {Colors.ACCENT_DIM};
        }}
    """


def success_button() -> str:
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.SUCCESS_DIM}, stop:1 {Colors.SUCCESS});
            color: {Colors.WHITE};
            border: none;
            border-radius: {Radius.MD};
            padding: 8px 16px;
            font-size: 12px;
            font-weight: {Fonts.WEIGHT_SEMIBOLD};
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.SUCCESS}, stop:1 #34d399);
        }}
        QPushButton:pressed {{
            background: #047857;
        }}
    """


def secondary_button() -> str:
    return f"""
        QPushButton {{
            background: {Colors.BG_ELEVATED};
            color: {Colors.TEXT_BODY};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.MD};
            padding: 8px 18px;
            font-size: {Fonts.SIZE_BODY};
            font-weight: {Fonts.WEIGHT_MEDIUM};
        }}
        QPushButton:hover {{
            background: {Colors.BG_HOVER};
            border-color: {Colors.BG_ACTIVE};
            color: {Colors.TEXT_PRIMARY};
        }}
    """


def ghost_button() -> str:
    return f"""
        QPushButton {{
            background: {Colors.TRANSPARENT};
            color: {Colors.TEXT_MUTED};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.SM};
            padding: 4px 12px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_ELEVATED};
            color: {Colors.TEXT_BODY};
            border-color: {Colors.BG_ACTIVE};
        }}
    """


def toolbar_label() -> str:
    return f"""
        font-size: 11px;
        color: {Colors.TEXT_MUTED};
        font-weight: {Fonts.WEIGHT_MEDIUM};
        padding: 0 2px;
        background: {Colors.TRANSPARENT};
        border: none;
        letter-spacing: 0.3px;
    """


def toolbar_value() -> str:
    return f"""
        font-size: 12px;
        color: {Colors.ACCENT};
        font-weight: {Fonts.WEIGHT_SEMIBOLD};
        font-family: {Fonts.MONO};
        padding: 0 4px;
        background: {Colors.TRANSPARENT};
        border: none;
    """


def separator() -> str:
    return f"color: {Colors.BORDER}; background: {Colors.BORDER}; max-width: 1px; margin: 4px 6px;"


def group_box() -> str:
    return f"""
        QGroupBox {{
            color: {Colors.ACCENT};
            border: 1px solid {Colors.BORDER};
            border-radius: {Radius.LG};
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


def info_label() -> str:
    return f"""
        color: {Colors.TEXT_MUTED};
        font-size: 11px;
        background: {Colors.TRANSPARENT};
        border: none;
    """


def status_dot(color: str) -> str:
    return f"color: {color}; font-size: 10px; padding: 0 4px; background: {Colors.TRANSPARENT};"
