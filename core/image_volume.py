import numpy as np


class ImageVolume:
    """封装医学图像的 3D 体数据及其元数据。"""

    def __init__(
        self,
        data: np.ndarray,
        spacing: tuple[float, ...] = (1.0, 1.0, 1.0),
        origin: tuple[float, ...] = (0.0, 0.0, 0.0),
        direction: tuple[float, ...] = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
        metadata: dict | None = None,
        file_path: str = "",
    ):
        self.data = data  # shape: (X, Y, Z) for 3D, (X, Y) for 2D
        self.spacing = spacing
        self.origin = origin
        self.direction = direction
        self.metadata = metadata or {}
        self.file_path = file_path

    @property
    def is_3d(self) -> bool:
        return self.data.ndim == 3

    @property
    def shape(self) -> tuple:
        return self.data.shape

    @property
    def dtype(self):
        return self.data.dtype

    def get_patient_name(self) -> str:
        return self.metadata.get("PatientName", "Unknown")

    def get_study_description(self) -> str:
        return self.metadata.get("StudyDescription", "Unknown")

    def get_modality(self) -> str:
        return self.metadata.get("Modality", "Unknown")

    def get_series_description(self) -> str:
        return self.metadata.get("SeriesDescription", "Unknown")

    def __repr__(self):
        return (
            f"ImageVolume(shape={self.shape}, dtype={self.dtype}, "
            f"modality={self.get_modality()}, spacing={self.spacing})"
        )
