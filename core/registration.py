"""基于 ANTs 的 SyNRA 配准模块，封装自 SyNRA.py。"""

import os
import numpy as np
import SimpleITK as sitk

from core.image_volume import ImageVolume


# ==================== 解剖部位窗位配置 ====================
WINDOW_SETTINGS = {
    "Abdomen": (-85, 165),
    "Brain": (0, 80),
    "Skull": (0, 800),
    "Extremities": (-400, 1000),
    "Liver": (-40, 160),
    "Lung": (-750, 422),
    "Pelvis": (-140, 210),
    "SkullBase": (-60, 140),
    "SpineA": (-35, 215),
    "SpineB": (-300, 1200),
    "Thorax": (-125, 225),
}


def truncate_ct_hu(image_path, window_min=None, window_max=None, z_segments=None):
    """CT HU 截断处理。"""
    if not os.path.exists(image_path):
        return None

    img = sitk.ReadImage(image_path)
    arr = sitk.GetArrayFromImage(img)
    arr[arr < -1000] = -1000

    if z_segments:
        for start_z, end_z, seg_min, seg_max in z_segments:
            start_z = max(0, start_z)
            end_z = min(arr.shape[0] - 1, end_z)
            if start_z <= end_z:
                arr[start_z:end_z + 1, :, :] = np.clip(
                    arr[start_z:end_z + 1, :, :], seg_min, seg_max
                )
    elif window_min is not None and window_max is not None:
        arr = np.clip(arr, window_min, window_max)

    new_img = sitk.GetImageFromArray(arr)
    new_img.CopyInformation(img)
    return new_img


DEFAULT_REG_PARAMS = {
    # 图像窗位
    "selected_window": "Lung",
    "use_z_segments": False,
    "z_segments_fixed": [],
    "z_segments_moving": [],
    # 仿射阶段
    "aff_metric": "mattes",
    "aff_sampling": 100,
    "aff_iterations": [2100, 1200, 1200, 10],
    "aff_shrink_factors": [6, 4, 2, 1],
    "aff_smoothing_sigmas": [5, 4, 2, 1],
    # SyN 阶段
    "syn_metric": "mattes",
    "syn_sampling": 20,
    "flow_sigma": 0.6,
    "total_sigma": 0.5,
    "reg_iterations": [400, 300, 200, 100],
    "mask_all_stages": True,
}


class SyNRARegistration:
    """基于 ANTs SyNRA 的 CT-to-RTCT 可变形配准。"""

    def __init__(self):
        self.params = dict(DEFAULT_REG_PARAMS)
        self._log_callback = None

    def set_log_callback(self, callback):
        self._log_callback = callback

    def _log(self, msg: str):
        if self._log_callback:
            self._log_callback(msg)

    def register(
        self,
        fixed_path: str,
        moving_path: str,
        pet_path: str | None = None,
        mask_path: str | None = None,
        output_dir: str | None = None,
        params: dict | None = None,
    ) -> dict:
        """执行 SyNRA 配准。

        Returns:
            {"ct": ImageVolume, "pet": ImageVolume|None, "mask": ImageVolume|None, "output_dir": str}
        """
        import ants

        p = dict(self.params)
        if params:
            p.update(params)

        if output_dir is None:
            output_dir = os.path.dirname(fixed_path)
        os.makedirs(output_dir, exist_ok=True)

        # --- 窗位设置 ---
        window_name = p.get("selected_window", "Lung")
        if window_name and window_name in WINDOW_SETTINGS:
            wmin, wmax = WINDOW_SETTINGS[window_name]
        else:
            wmin, wmax = None, None

        z_seg_fix = p.get("z_segments_fixed") if p.get("use_z_segments") else None
        z_seg_mov = p.get("z_segments_moving") if p.get("use_z_segments") else None

        self._log(f"窗位: {window_name or '仅空气截断'}  W:[{wmin}, {wmax}]")

        # --- 读取原始图像 ---
        fi_original = ants.image_read(fixed_path)
        mi_original = ants.image_read(moving_path)

        # HU 截断用于配准计算
        fix_sitk = truncate_ct_hu(fixed_path, wmin, wmax, z_seg_fix)
        move_sitk = truncate_ct_hu(moving_path, wmin, wmax, z_seg_mov)

        fi = ants.from_sitk(fix_sitk) if fix_sitk else fi_original
        mi = ants.from_sitk(move_sitk) if move_sitk else mi_original

        # PET 和 Mask
        pet = ants.image_read(pet_path) if pet_path and os.path.exists(pet_path) else None
        mask = ants.image_read(mask_path) if mask_path and os.path.exists(mask_path) else None

        if mask is not None:
            self._log(f"使用掩码: {os.path.basename(mask_path)}")

        # --- 配准 ---
        self._log("开始 SyNRA 配准...")
        reg = ants.registration(
            fixed=fi,
            moving=mi,
            type_of_transform="SyNRA",
            aff_metric=p["aff_metric"],
            aff_sampling=p["aff_sampling"],
            aff_iterations=tuple(p["aff_iterations"]),
            aff_shrink_factors=tuple(p["aff_shrink_factors"]),
            aff_smoothing_sigmas=tuple(p["aff_smoothing_sigmas"]),
            syn_metric=p["syn_metric"],
            syn_sampling=p["syn_sampling"],
            flow_sigma=p["flow_sigma"],
            total_sigma=p["total_sigma"],
            reg_iterations=tuple(p["reg_iterations"]),
            mask=mask,
            mask_all_stages=p["mask_all_stages"],
            verbose=True,
        )
        self._log("配准完成！")

        # --- 应用变换 ---
        self._log("应用变换到 CT...")
        ct_final = ants.apply_transforms(
            fixed=fi_original, moving=mi_original,
            transformlist=reg["fwdtransforms"],
            interpolator="linear", defaultvalue=-1000,
        )

        pet_final = None
        if pet is not None:
            self._log("应用变换到 PET...")
            pet_raw = ants.apply_transforms(
                fixed=fi_original, moving=pet,
                transformlist=reg["fwdtransforms"],
                interpolator="nearestNeighbor", defaultvalue=0,
            )
            pet_data = pet_raw.numpy()
            pet_data[pet_data < 0] = 0
            pet_final = pet_raw.new_image_like(pet_data.astype("float32"))

        mask_final = None
        if mask is not None:
            self._log("应用变换到 Mask...")
            mask_final = ants.apply_transforms(
                fixed=fi_original, moving=mask,
                transformlist=reg["fwdtransforms"],
                interpolator="nearestNeighbor", defaultvalue=0,
            )

        # --- 保存结果 ---
        ct_out = os.path.join(output_dir, "FIT_CT.nii")
        ants.image_write(ct_final, ct_out)
        self._log(f"已保存: {ct_out}")

        pet_out = None
        if pet_final is not None:
            pet_out = os.path.join(output_dir, "FIT_PET.nii")
            pet_final.to_filename(pet_out)
            self._log(f"已保存: {pet_out}")

        mask_out = None
        if mask_final is not None:
            mask_out = os.path.join(output_dir, "FIT_ROI.nii.gz")
            ants.image_write(mask_final, mask_out)
            self._log(f"已保存: {mask_out}")

        # --- 转为 ImageVolume 返回 ---
        def ants_to_volume(aimg, path=""):
            arr = aimg.numpy()
            sp = aimg.spacing
            return ImageVolume(
                data=arr.astype(np.float32),
                spacing=sp,
                file_path=path,
            )

        return {
            "ct": ants_to_volume(ct_final, ct_out),
            "pet": ants_to_volume(pet_final, pet_out) if pet_final else None,
            "mask": ants_to_volume(mask_final, mask_out) if mask_final else None,
            "output_dir": output_dir,
        }


# ==================== 多模态配准 ====================

MULTIMODAL_REG_PARAMS = {
    "mri_to_pet": {
        "aff_metric": "mattes",
        "aff_sampling": 48,
        "aff_iterations": [2100, 1500, 800, 500],
        "aff_shrink_factors": [4, 2, 1, 1],
        "aff_smoothing_sigmas": [2, 1, 0.5, 0],
        "syn_metric": "mattes",
        "syn_sampling": 32,
        "flow_sigma": 2,
        "total_sigma": 1,
        "reg_iterations": [100, 75, 50, 25],
    },
    "pet_to_mri": {
        "aff_metric": "mattes",
        "aff_sampling": 100,
        "aff_iterations": [2100, 1500, 800, 500],
        "aff_shrink_factors": [4, 2, 1, 1],
        "aff_smoothing_sigmas": [2, 1, 0.5, 0],
        "syn_metric": "mattes",
        "syn_sampling": 20,
        "flow_sigma": 2,
        "total_sigma": 1,
        "reg_iterations": [100, 75, 50, 25],
    },
}


def resample_pet_to_target(image_path, target_size=(512, 512, 36)):
    """将 PET 图像重采样到目标尺寸，保持物理空间范围。"""
    sitk_img = sitk.ReadImage(image_path)
    current_size = sitk_img.GetSize()
    current_spacing = sitk_img.GetSpacing()
    original_origin = sitk_img.GetOrigin()
    original_direction = sitk_img.GetDirection()
    original_pixel_id = sitk_img.GetPixelIDValue()

    if current_size[0] == target_size[0] and current_size[1] == target_size[1] and current_size[2] == target_size[2]:
        img_array = sitk.GetArrayFromImage(sitk_img)
        img_array = np.transpose(img_array, (2, 1, 0))
        return img_array, current_spacing, original_origin, original_direction

    original_size_mm = (
        current_size[0] * current_spacing[0],
        current_size[1] * current_spacing[1],
        current_size[2] * current_spacing[2],
    )
    target_spacing = (
        original_size_mm[0] / target_size[0],
        original_size_mm[1] / target_size[1],
        original_size_mm[2] / target_size[2],
    )

    transform = sitk.Transform()
    transform.SetIdentity()
    reference_image = sitk.Image(target_size, original_pixel_id)
    reference_image.SetSpacing(target_spacing)
    reference_image.SetOrigin(original_origin)
    reference_image.SetDirection(original_direction)

    resampled_sitk = sitk.Resample(sitk_img, reference_image, transform, sitk.sitkLinear, 0.0, original_pixel_id)
    resampled_array = sitk.GetArrayFromImage(resampled_sitk)
    resampled_array = np.transpose(resampled_array, (2, 1, 0))

    return resampled_array, resampled_sitk.GetSpacing(), original_origin, original_direction


def resample_mri_to_target(image_path, target_xy=512, min_z=36):
    """将 MRI 重采样到 target_xy x target_xy x max(Z, min_z)，保持物理空间。"""
    sitk_img = sitk.ReadImage(image_path)
    current_size = sitk_img.GetSize()
    current_spacing = sitk_img.GetSpacing()
    original_origin = sitk_img.GetOrigin()
    original_direction = sitk_img.GetDirection()
    original_pixel_id = sitk_img.GetPixelIDValue()

    need_pad_z = current_size[2] < min_z
    final_z = max(current_size[2], min_z)

    if current_size[0] == target_xy and current_size[1] == target_xy and not need_pad_z:
        img_array = sitk.GetArrayFromImage(sitk_img)
        img_array = np.transpose(img_array, (2, 1, 0))
        return img_array, current_spacing, original_origin, original_direction

    original_size_mm = (
        current_size[0] * current_spacing[0],
        current_size[1] * current_spacing[1],
        current_size[2] * current_spacing[2],
    )
    target_spacing = (
        original_size_mm[0] / target_xy,
        original_size_mm[1] / target_xy,
        current_spacing[2],
    )
    target_size = (target_xy, target_xy, current_size[2])

    transform = sitk.Transform()
    transform.SetIdentity()
    reference_image = sitk.Image(target_size, original_pixel_id)
    reference_image.SetSpacing(target_spacing)
    reference_image.SetOrigin(original_origin)
    reference_image.SetDirection(original_direction)

    resampled_sitk = sitk.Resample(sitk_img, reference_image, transform, sitk.sitkLinear, 0.0, original_pixel_id)

    if need_pad_z:
        resampled_array = sitk.GetArrayFromImage(resampled_sitk)
        pad_z = final_z - current_size[2]
        pad_slices = np.zeros((pad_z, target_xy, target_xy), dtype=resampled_array.dtype)
        resampled_array = np.concatenate((resampled_array, pad_slices), axis=0)
        final_spacing = list(resampled_sitk.GetSpacing())
        resampled_sitk = sitk.GetImageFromArray(resampled_array)
        resampled_sitk.SetSpacing(final_spacing)
        resampled_sitk.SetOrigin(original_origin)
        resampled_sitk.SetDirection(original_direction)

    result_array = sitk.GetArrayFromImage(resampled_sitk)
    result_array = np.transpose(result_array, (2, 1, 0))
    return result_array, resampled_sitk.GetSpacing(), original_origin, original_direction


def correct_mri_direction(arr, direction, target_direction=None):
    """修正 MRI 方向，翻转负方向轴。"""
    if target_direction is None:
        target_direction = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])

    if not np.allclose(direction, target_direction, atol=0.01):
        if direction[0, 0] < 0:
            arr = np.flip(arr, axis=0)
        if direction[1, 1] < 0:
            arr = np.flip(arr, axis=1)
        if direction[2, 2] < 0:
            arr = np.flip(arr, axis=2)
        return arr, target_direction
    return arr, direction


class MultimodalRegistration:
    """多模态配准引擎，支持 MRI↔PET 配准。"""

    def __init__(self):
        self._log_callback = None

    def set_log_callback(self, callback):
        self._log_callback = callback

    def _log(self, msg: str):
        if self._log_callback:
            self._log_callback(msg)

    def register(
        self,
        mode: str,
        mri_path: str,
        pet_path: str,
        output_dir: str | None = None,
        params: dict | None = None,
    ) -> dict:
        """执行多模态配准。

        Args:
            mode: "mri_to_pet" 或 "pet_to_mri"
            mri_path: MRI 文件路径
            pet_path: PET 文件路径
            output_dir: 输出目录
            params: 配准参数覆盖

        Returns:
            {"fixed": ImageVolume, "moving_final": ImageVolume, "output_dir": str}
        """
        import ants

        if mode not in ("mri_to_pet", "pet_to_mri"):
            raise ValueError(f"不支持的配准模式: {mode}")

        p = dict(MULTIMODAL_REG_PARAMS[mode])
        if params:
            p.update(params)

        if output_dir is None:
            output_dir = os.path.dirname(mri_path)
        os.makedirs(output_dir, exist_ok=True)

        if mode == "mri_to_pet":
            return self._register_mri_to_pet(mri_path, pet_path, output_dir, p)
        else:
            return self._register_pet_to_mri(mri_path, pet_path, output_dir, p)

    def _register_mri_to_pet(self, mri_path, pet_path, output_dir, p):
        import ants

        self._log("=== MRI → PET 配准 ===")
        self._log("重采样 PET 到 512x512x36...")
        pet_arr, pet_sp, pet_origin, pet_dir = resample_pet_to_target(pet_path)
        self._log(f"PET 重采样完成: shape={pet_arr.shape}, spacing={pet_sp}")

        # 保存重采样后的 PET
        pet_ants = ants.from_numpy(pet_arr)
        pet_ants.set_spacing(pet_sp)
        pet_ants.set_origin(pet_origin)
        pet_ants.set_direction(np.array(pet_dir).reshape(3, 3) if hasattr(pet_dir, '__len__') else pet_dir)
        fixed = pet_ants

        # 读取并修正 MRI
        self._log("读取 MRI...")
        mri_ants = ants.image_read(mri_path)
        mri_arr = mri_ants.numpy()
        mri_arr, new_dir = correct_mri_direction(mri_arr, mri_ants.direction)
        mri_corrected = ants.from_numpy(mri_arr)
        mri_corrected.set_spacing(mri_ants.spacing)
        mri_corrected.set_origin(mri_ants.origin)
        mri_corrected.set_direction(new_dir)
        moving = mri_corrected

        self._log(f"固定像(PET): shape={fixed.shape}, spacing={fixed.spacing}")
        self._log(f"移动像(MRI): shape={moving.shape}, spacing={moving.spacing}")

        # 执行配准
        self._log("开始 SyNRA 配准 (MRI → PET)...")
        reg = ants.registration(
            fixed=fixed, moving=moving,
            type_of_transform="SyNRA",
            aff_metric=p["aff_metric"],
            aff_sampling=p["aff_sampling"],
            aff_iterations=tuple(p["aff_iterations"]),
            aff_shrink_factors=tuple(p["aff_shrink_factors"]),
            aff_smoothing_sigmas=tuple(p["aff_smoothing_sigmas"]),
            syn_metric=p["syn_metric"],
            syn_sampling=p["syn_sampling"],
            flow_sigma=p["flow_sigma"],
            total_sigma=p["total_sigma"],
            reg_iterations=tuple(p["reg_iterations"]),
            verbose=True,
        )
        self._log("配准完成！")

        # 应用变换
        self._log("应用变换到 MRI...")
        mri_final = ants.apply_transforms(
            fixed=fixed, moving=moving,
            transformlist=reg["fwdtransforms"],
            interpolator="linear", defaultvalue=0,
        )

        # 保持原始数据类型
        mri_final_data = mri_final.numpy().astype(mri_ants.numpy().dtype)
        mri_final = ants.from_numpy(mri_final_data)
        mri_final.set_spacing(fixed.spacing)
        mri_final.set_origin(fixed.origin)
        mri_final.set_direction(fixed.direction)

        # 保存结果
        pet_out = os.path.join(output_dir, "PETnew.nii.gz")
        ants.image_write(fixed, pet_out)
        self._log(f"已保存重采样 PET: {pet_out}")

        mri_out = os.path.join(output_dir, "FIT_MRI_to_PET.nii.gz")
        ants.image_write(mri_final, mri_out)
        self._log(f"已保存配准后 MRI: {mri_out}")

        return {
            "fixed": _ants_to_volume(fixed, pet_out),
            "moving_final": _ants_to_volume(mri_final, mri_out),
            "output_dir": output_dir,
        }

    def _register_pet_to_mri(self, mri_path, pet_path, output_dir, p):
        import ants

        self._log("=== PET → MRI 配准 ===")
        self._log("重采样 MRI 到 512x512...")
        mri_arr, mri_sp, mri_origin, mri_dir = resample_mri_to_target(mri_path)
        self._log(f"MRI 重采样完成: shape={mri_arr.shape}, spacing={mri_sp}")

        mri_ants = ants.from_numpy(mri_arr)
        mri_ants.set_spacing(mri_sp)
        mri_ants.set_origin(mri_origin)
        mri_ants.set_direction(np.array(mri_dir).reshape(3, 3) if hasattr(mri_dir, '__len__') else mri_dir)
        fixed = mri_ants

        # 读取 PET
        self._log("读取 PET...")
        moving = ants.image_read(pet_path)
        original_pet_dtype = moving.numpy().dtype

        self._log(f"固定像(MRI): shape={fixed.shape}, spacing={fixed.spacing}")
        self._log(f"移动像(PET): shape={moving.shape}, spacing={moving.spacing}")

        # 执行配准
        self._log("开始 SyNRA 配准 (PET → MRI)...")
        reg = ants.registration(
            fixed=fixed, moving=moving,
            type_of_transform="SyNRA",
            aff_metric=p["aff_metric"],
            aff_sampling=p["aff_sampling"],
            aff_iterations=tuple(p["aff_iterations"]),
            aff_shrink_factors=tuple(p["aff_shrink_factors"]),
            aff_smoothing_sigmas=tuple(p["aff_smoothing_sigmas"]),
            syn_metric=p["syn_metric"],
            syn_sampling=p["syn_sampling"],
            flow_sigma=p["flow_sigma"],
            total_sigma=p["total_sigma"],
            reg_iterations=tuple(p["reg_iterations"]),
            verbose=True,
        )
        self._log("配准完成！")

        # 应用变换
        self._log("应用变换到 PET...")
        pet_final = ants.apply_transforms(
            fixed=fixed, moving=moving,
            transformlist=reg["fwdtransforms"],
            interpolator="nearestNeighbor", defaultvalue=0,
        )

        # 保持原始数据类型
        pet_final_data = pet_final.numpy().astype(original_pet_dtype)
        pet_final = ants.from_numpy(pet_final_data)
        pet_final.set_spacing(fixed.spacing)
        pet_final.set_origin(fixed.origin)
        pet_final.set_direction(fixed.direction)

        # 保存结果
        mri_out = os.path.join(output_dir, "MRInew.nii.gz")
        ants.image_write(fixed, mri_out)
        self._log(f"已保存重采样 MRI: {mri_out}")

        pet_out = os.path.join(output_dir, "FIT_PET_to_MRI.nii")
        ants.image_write(pet_final, pet_out)
        self._log(f"已保存配准后 PET: {pet_out}")

        return {
            "fixed": _ants_to_volume(fixed, mri_out),
            "moving_final": _ants_to_volume(pet_final, pet_out),
            "output_dir": output_dir,
        }


def _ants_to_volume(aimg, path=""):
    """将 ANTs 图像转为 ImageVolume。"""
    arr = aimg.numpy()
    sp = aimg.spacing
    return ImageVolume(
        data=arr.astype(np.float32),
        spacing=sp,
        file_path=path,
    )
