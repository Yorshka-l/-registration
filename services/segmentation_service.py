"""分割服务 — 封装 PyTorch 模型推理。"""

from core.segmentation import Segmentor
from core.image_volume import ImageVolume


class SegmentationService:
    """图像分割服务。"""

    def __init__(self):
        self._segmentor = Segmentor()

    def load_model(self, model_path: str, device: str = "auto"):
        self._segmentor.load_model(model_path, device)

    def predict(self, volume: ImageVolume, threshold: float = 0.5):
        return self._segmentor.predict(volume, threshold)

    @property
    def is_model_loaded(self) -> bool:
        return self._segmentor.is_loaded

    @property
    def model_info(self) -> dict:
        return {
            "path": self._segmentor.model_path,
            "device": self._segmentor.device_name,
            "loaded": self._segmentor.is_loaded,
        }
