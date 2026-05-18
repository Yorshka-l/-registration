"""图像相关状态。"""

from dataclasses import dataclass, field


@dataclass
class ImageInfo:
    """已加载图像的元信息。"""
    name: str = ""
    path: str = ""
    modality: str = ""
    shape: tuple = ()
    spacing: tuple = ()


@dataclass
class WindowLevel:
    """窗宽窗位状态。"""
    width: int = 400
    level: int = 40


@dataclass
class ImageState:
    """图像查看器状态。"""
    current_image: ImageInfo | None = None
    loaded_images: list[ImageInfo] = field(default_factory=list)
    window_level: WindowLevel = field(default_factory=WindowLevel)
    colormap: str = "灰度"
    slice_indices: dict = field(default_factory=lambda: {"axial": 0, "coronal": 0, "sagittal": 0})
