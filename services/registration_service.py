"""配准服务 — 封装 SyNRA 和多模态配准。"""

from core.registration import SyNRARegistration, MultimodalRegistration


class RegistrationService:
    """配准执行服务。"""

    def __init__(self):
        self._synra = SyNRARegistration()
        self._multimodal = MultimodalRegistration()

    def run_synra(self, fixed: str, moving: str, pet: str = None,
                  mask: str = None, output_dir: str = None,
                  params: dict = None, log_callback=None) -> dict:
        """执行 SyNRA CT-to-RTCT 配准。"""
        if log_callback:
            self._synra.set_log_callback(log_callback)
        return self._synra.register(
            fixed, moving, pet_path=pet, mask_path=mask,
            output_dir=output_dir, params=params,
        )

    def run_multimodal(self, mode: str, mri_path: str, pet_path: str,
                       output_dir: str = None, params: dict = None,
                       log_callback=None) -> dict:
        """执行多模态配准 (MRI<->PET)。"""
        if log_callback:
            self._multimodal.set_log_callback(log_callback)
        return self._multimodal.register(
            mode=mode, mri_path=mri_path, pet_path=pet_path,
            output_dir=output_dir, params=params,
        )

    def get_window_settings(self) -> dict:
        from core.registration import WINDOW_SETTINGS
        return WINDOW_SETTINGS
