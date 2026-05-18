"""图像服务 — 封装 core/image_io 的业务逻辑。"""

import os
from core.image_io import load_image as _core_load, save_image as _core_save
from core.image_volume import ImageVolume
from state.image_state import ImageInfo


class ImageService:
    """图像加载/保存/信息查询服务。"""

    def load(self, path: str) -> tuple[ImageVolume, ImageInfo]:
        """加载图像，返回 (volume, info)。"""
        vol = _core_load(path)
        info = ImageInfo(
            name=os.path.basename(path),
            path=path,
            modality=vol.get_modality(),
            shape=vol.shape,
            spacing=vol.spacing,
        )
        return vol, info

    def save(self, volume: ImageVolume, path: str):
        _core_save(volume, path)

    def get_supported_extensions(self) -> set[str]:
        return {".dcm", ".nii", ".nii.gz", ".mha", ".mhd", ".nrrd"}

    def is_supported(self, path: str) -> bool:
        lower = path.lower()
        return any(lower.endswith(ext) for ext in self.get_supported_extensions())
