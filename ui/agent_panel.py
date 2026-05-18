from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QComboBox, QLabel, QLineEdit,
    QDialog, QFormLayout, QDialogButtonBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from config import API_PRESETS, load_config, save_config
from ui.styles.tokens import Colors
from ui.styles.components import GlassPanel


class APISettingsDialog(QDialog):
    """API 设置对话框 — 支持预设和自定义端点。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agent API 设置")
        self.setMinimumWidth(520)
        self.setMinimumHeight(400)
        self._cfg = load_config()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: #080c14;
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                background: transparent;
                font-size: 13px;
            }}
            QComboBox {{
                background-color: #0a0e14;
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QComboBox QAbstractItemView {{
                background-color: rgba(10, 14, 22, 0.95);
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                selection-background-color: rgba(0, 180, 216, 0.20);
                selection-color: {Colors.WHITE};
                padding: 4px;
            }}
            QLineEdit {{
                background-color: #0a0e14;
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.ACCENT};
            }}
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.04);
                color: {Colors.TEXT_BODY};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                border-color: rgba(255, 255, 255, 0.12);
                color: {Colors.TEXT_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("API 配置")
        header.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
            margin-bottom: 8px;
        """)
        layout.addWidget(header)

        # Subtitle
        subtitle = QLabel("选择 LLM 服务提供商并配置连接参数")
        subtitle.setStyleSheet(f"""
            font-size: 13px;
            color: {Colors.TEXT_MUTED};
            margin-bottom: 12px;
        """)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Provider selection
        self._provider = QComboBox()
        for name in API_PRESETS:
            self._provider.addItem(name)
        self._provider.addItem("自定义")
        self._provider.currentIndexChanged.connect(self._on_provider_changed)
        form.addRow("提供商:", self._provider)

        # Base URL
        self._base_url = QLineEdit()
        self._base_url.setPlaceholderText("https://api.example.com/v1")
        form.addRow("API 地址:", self._base_url)

        # API Key
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.Password)
        self._api_key.setPlaceholderText("sk-...")
        form.addRow("API Key:", self._api_key)

        # Model
        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        form.addRow("模型:", self._model_combo)

        layout.addLayout(form)
        layout.addStretch()

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)

        # Style the OK button as primary
        ok_btn = btns.button(QDialogButtonBox.Ok)
        ok_btn.setText("保存")
        ok_btn.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Colors.ACCENT_DIM}, stop:1 {Colors.ACCENT});
            color: {Colors.WHITE};
            border: none;
            border-radius: 8px;
            padding: 8px 24px;
            font-weight: 600;
        """)

        cancel_btn = btns.button(QDialogButtonBox.Cancel)
        cancel_btn.setText("取消")

        layout.addWidget(btns)

        # Load current config
        self._load_current()

    def _load_current(self):
        cfg = self._cfg
        provider = cfg.get("custom_provider_name", "自定义")
        base_url = cfg.get("custom_base_url", "")
        api_key = cfg.get("custom_api_key", "")
        model = cfg.get("custom_model", "")

        self._provider.blockSignals(True)
        idx = self._provider.findText(provider)
        if idx >= 0:
            self._provider.setCurrentIndex(idx)
        else:
            self._provider.setCurrentIndex(self._provider.count() - 1)
        self._provider.blockSignals(False)

        self._on_provider_changed_load(base_url, api_key, model)

    def _on_provider_changed(self, index):
        name = self._provider.currentText()
        self._api_key.clear()
        if name in API_PRESETS:
            preset = API_PRESETS[name]
            self._base_url.setText(preset["base_url"])
            self._model_combo.clear()
            self._model_combo.addItems(preset["models"])
            if name == "Ollama (本地)":
                self._api_key.setPlaceholderText("本地模型通常不需要 key")
            else:
                self._api_key.setPlaceholderText("sk-...")
        else:
            self._model_combo.clear()
            self._api_key.setPlaceholderText("sk-...")

    def _on_provider_changed_load(self, base_url, api_key, model):
        name = self._provider.currentText()
        if name in API_PRESETS:
            preset = API_PRESETS[name]
            if not base_url:
                self._base_url.setText(preset["base_url"])
            else:
                self._base_url.setText(base_url)
            self._model_combo.clear()
            self._model_combo.addItems(preset["models"])
            if name == "Ollama (本地)":
                self._api_key.setPlaceholderText("本地模型通常不需要 key")
            else:
                self._api_key.setPlaceholderText("sk-...")
        else:
            if base_url:
                self._base_url.setText(base_url)
            self._model_combo.clear()
            self._api_key.setPlaceholderText("sk-...")
        if api_key:
            self._api_key.setText(api_key)
        if model:
            self._model_combo.setCurrentText(model)

    def _save(self):
        cfg = self._cfg
        cfg["custom_provider_name"] = self._provider.currentText()
        cfg["custom_base_url"] = self._base_url.text().strip()
        cfg["custom_api_key"] = self._api_key.text().strip()
        cfg["custom_model"] = self._model_combo.currentText().strip()
        save_config(cfg)
        self.accept()

    def get_settings(self) -> dict:
        return {
            "provider_name": self._provider.currentText(),
            "base_url": self._base_url.text().strip(),
            "api_key": self._api_key.text().strip(),
            "model": self._model_combo.currentText().strip(),
        }


class AgentPanel(QWidget):
    """AI Agent 对话面板。"""

    message_sent = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Top bar with provider controls
        top_frame = GlassPanel(self, radius=8, opacity=0.08, border_opacity=0.06)
        top_frame.setFixedHeight(40)
        top = QHBoxLayout(top_frame)
        top.setContentsMargins(12, 0, 12, 0)
        top.setSpacing(8)

        # Provider icon/label
        provider_icon = QLabel("AI")
        provider_icon.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 700;
            color: {Colors.ACCENT};
            background: {Colors.ACCENT_GLOW};
            border-radius: 4px;
            padding: 2px 6px;
            border: none;
        """)
        top.addWidget(provider_icon)

        self._provider_combo = QComboBox()
        self._provider_combo.addItems(["自定义 API", "Ollama (本地)"])
        self._provider_combo.setStyleSheet(f"""
            QComboBox {{
                background: transparent;
                color: {Colors.TEXT_BODY};
                border: none;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                selection-background-color: {Colors.ACCENT};
            }}
        """)
        top.addWidget(self._provider_combo)

        self._settings_btn = QPushButton("设置")
        self._settings_btn.setObjectName("settings_btn")
        self._settings_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_MUTED};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_BODY};
                border-color: {Colors.BG_ACTIVE};
            }}
        """)
        self._settings_btn.clicked.connect(self._open_settings)
        top.addWidget(self._settings_btn)
        top.addStretch()

        self._clear_btn = QPushButton("清空")
        self._clear_btn.setObjectName("clear_btn")
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_MUTED};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_BODY};
                border-color: {Colors.BG_ACTIVE};
            }}
        """)
        self._clear_btn.clicked.connect(self._clear_history)
        top.addWidget(self._clear_btn)

        layout.addWidget(top_frame)

        # Provider info label
        self._provider_info = QLabel("")
        self._provider_info.setStyleSheet(f"""
            color: {Colors.TEXT_DISABLED};
            font-size: 11px;
            padding: 2px 4px;
            background: transparent;
        """)
        layout.addWidget(self._provider_info)

        # Chat history with modern styling
        self._history = QTextEdit()
        self._history.setReadOnly(True)
        self._history.setPlaceholderText("与 AI Agent 对话，输入指令来执行图像处理任务...")
        self._history.setStyleSheet(f"""
            QTextEdit {{
                background-color: #080c14;
                color: {Colors.TEXT_BODY};
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.5;
            }}
        """)
        layout.addWidget(self._history, stretch=1)

        # Input area with glass styling
        input_frame = GlassPanel(self, radius=10, opacity=0.08, border_opacity=0.06)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(8)

        self._input = QTextEdit()
        self._input.setMaximumHeight(56)
        self._input.setPlaceholderText("输入指令，例如：帮我把当前图像做分割...")
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                color: {Colors.TEXT_PRIMARY};
                border: none;
                padding: 4px 8px;
                font-size: 13px;
            }}
        """)
        self._input.installEventFilter(self)
        input_layout.addWidget(self._input, stretch=1)

        self._send_btn = QPushButton("发送")
        self._send_btn.setObjectName("send_btn")
        self._send_btn.setFixedSize(80, 40)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {Colors.ACCENT_DIM}, stop:1 {Colors.ACCENT});
                color: {Colors.WHITE};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0096c7, stop:1 {Colors.ACCENT_LIGHT});
            }}
            QPushButton:pressed {{
                background: {Colors.ACCENT_DIM};
            }}
            QPushButton:disabled {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_DISABLED};
            }}
        """)
        self._send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(self._send_btn)

        layout.addWidget(input_frame)

        self._update_info()

    def _open_settings(self):
        dlg = APISettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._update_info()

    def _update_info(self):
        cfg = load_config()
        name = cfg.get("custom_provider_name", "")
        model = cfg.get("custom_model", "")
        url = cfg.get("custom_base_url", "")
        if name and model:
            self._provider_info.setText(f"当前: {name} / {model}  ({url})")
        else:
            self._provider_info.setText("请点击「设置」配置 API")

    def _send_message(self):
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._append_message("用户", text)
        self._input.clear()
        self.message_sent.emit(text)

    def _clear_history(self):
        self._history.clear()

    def _append_message(self, role: str, text: str):
        if role == "用户":
            bubble_bg = "rgba(0, 180, 216, 0.12)"
            border_color = "rgba(0, 180, 216, 0.25)"
            name_color = Colors.ACCENT
            align = "right"
        else:
            bubble_bg = "rgba(255, 255, 255, 0.04)"
            border_color = "rgba(255, 255, 255, 0.08)"
            name_color = Colors.SUCCESS
            align = "left"

        self._history.append(
            f'<div style="margin: 8px 0; text-align: {align};">'
            f'<span style="color: {name_color}; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;">{role}</span>'
            f'</div>'
            f'<div style="background: {bubble_bg}; border: 1px solid {border_color}; '
            f'border-radius: 10px; padding: 10px 14px; margin: 2px 0 12px 0; '
            f'text-align: left; color: {Colors.TEXT_BODY}; font-size: 13px; line-height: 1.5;">'
            f'{text}</div>'
        )
        # Auto-scroll to bottom
        sb = self._history.verticalScrollBar()
        sb.setValue(sb.maximum())

    def append_assistant_message(self, text: str):
        self._append_message("Agent", text)

    def append_system_message(self, text: str):
        self._history.append(
            f'<div style="text-align: center; margin: 8px 0;">'
            f'<span style="background: rgba(107, 125, 141, 0.10); border: 1px solid rgba(107, 125, 141, 0.15); '
            f'border-radius: 12px; padding: 4px 14px; color: {Colors.TEXT_MUTED}; font-size: 11px; font-style: italic;">'
            f'{text}</span></div>'
        )
        sb = self._history.verticalScrollBar()
        sb.setValue(sb.maximum())

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent, Qt
        if obj == self._input and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if not (event.modifiers() & Qt.ShiftModifier):
                    self._send_message()
                    return True
        return super().eventFilter(obj, event)
