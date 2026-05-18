import sys
import os
import traceback

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt


def excepthook(exc_type, exc_value, exc_tb):
    """全局异常处理，防止闪退。"""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"[未捕获异常]\n{msg}", file=sys.stderr)
    try:
        QMessageBox.critical(None, "程序错误", f"发生未捕获的异常:\n\n{msg}")
    except Exception:
        pass


sys.excepthook = excepthook


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MedImager")
    app.setStyle("Fusion")

    # High DPI font rendering
    from PySide6.QtGui import QFont
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)

    # Load stylesheet
    style_path = os.path.join(os.path.dirname(__file__), "assets", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    from state.app_state import AppState
    from services.image_service import ImageService
    from services.registration_service import RegistrationService
    from services.segmentation_service import SegmentationService
    from services.agent_service import AgentService
    from services.worker_manager import WorkerManager

    state = AppState()
    image_svc = ImageService()
    reg_svc = RegistrationService()
    seg_svc = SegmentationService()
    agent_svc = AgentService()
    workers = WorkerManager()

    from ui.main_window import MainWindow
    window = MainWindow(state, image_svc, reg_svc, seg_svc, agent_svc, workers)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
