"""全局应用状态 + PySide6 信号总线。"""

from PySide6.QtCore import QObject, Signal
from state.image_state import ImageState, ImageInfo, WindowLevel


class AppState(QObject):
    """应用全局状态，通过信号通知 UI 更新。"""

    # 图像信号
    image_loaded = Signal(ImageInfo)
    image_list_changed = Signal(list)
    window_level_changed = Signal(int, int)
    colormap_changed = Signal(str)
    slice_changed = Signal(str, int)

    # 配准信号
    registration_started = Signal()
    registration_progress = Signal(int)
    registration_finished = Signal(dict)
    registration_failed = Signal(str)
    registration_log = Signal(str)

    # 分割信号
    segmentation_started = Signal()
    segmentation_finished = Signal(object)
    segmentation_failed = Signal(str)

    # Agent 信号
    agent_message_sent = Signal(str)
    agent_reply_received = Signal(str)
    agent_error = Signal(str)
    agent_thinking = Signal()

    # 状态指示
    status_changed = Signal(str, str)  # (state: "ready"|"busy"|"error", message)

    def __init__(self):
        super().__init__()
        self.image = ImageState()

    def set_image(self, info: ImageInfo):
        self.image.current_image = info
        if info not in self.image.loaded_images:
            self.image.loaded_images.insert(0, info)
        self.image_loaded.emit(info)
        self.image_list_changed.emit(self.image.loaded_images)

    def set_window_level(self, width: int, level: int):
        self.image.window_level = WindowLevel(width, level)
        self.window_level_changed.emit(width, level)

    def set_colormap(self, name: str):
        self.image.colormap = name
        self.colormap_changed.emit(name)

    def get_loaded_image_paths(self) -> list[str]:
        return [img.path for img in self.image.loaded_images]
