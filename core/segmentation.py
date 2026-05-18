import numpy as np

from core.image_volume import ImageVolume


class Segmentor:
    """PyTorch 分割模型加载与推理。"""

    def __init__(self):
        self._model = None
        self._device = None
        self._model_path = ""

    def load_model(self, model_path: str, device: str = "auto"):
        """加载 PyTorch 模型。

        Args:
            model_path: .pth 模型文件路径。
            device: "auto", "cpu", 或 "cuda"。
        """
        import torch

        if device == "auto":
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        elif device == "cuda":
            self._device = torch.device("cuda")
        else:
            self._device = torch.device("cpu")

        self._model = torch.load(model_path, map_location=self._device, weights_only=False)
        self._model.eval()
        self._model.to(self._device)
        self._model_path = model_path

    def predict(
        self,
        volume: ImageVolume,
        threshold: float = 0.5,
    ) -> np.ndarray:
        """对图像体数据执行分割推理。

        Args:
            volume: 输入图像。
            threshold: 二值化阈值。

        Returns:
            分割掩码，numpy 数组，与输入同形状。
        """
        if self._model is None:
            raise RuntimeError("请先加载模型")

        import torch

        data = volume.data

        # Normalize to [0, 1]
        d_min, d_max = data.min(), data.max()
        if d_max > d_min:
            normed = (data - d_min) / (d_max - d_min)
        else:
            normed = np.zeros_like(data)

        # Add batch and channel dimensions: (1, 1, X, Y, Z)
        tensor = torch.from_numpy(normed).float().unsqueeze(0).unsqueeze(0)
        tensor = tensor.to(self._device)

        with torch.no_grad():
            output = self._model(tensor)

        # Remove batch dim, apply sigmoid if needed
        output = output.squeeze(0)
        if output.shape[0] == 1:
            mask = torch.sigmoid(output).cpu().numpy()[0]
        else:
            mask = torch.softmax(output, dim=0).cpu().numpy()

        # Threshold for binary mask
        if mask.ndim == 3:
            mask = (mask > threshold).astype(np.float32)
        elif mask.ndim == 4:
            # Multi-class: take argmax
            mask = np.argmax(mask, axis=0).astype(np.float32)

        return mask

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def model_path(self) -> str:
        return self._model_path

    @property
    def device_name(self) -> str:
        return str(self._device) if self._device else "N/A"
