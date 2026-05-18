import os
import numpy as np
import SimpleITK as sitk
import pydicom

from core.image_volume import ImageVolume


SUPPORTED_EXTENSIONS = {".dcm", ".nii", ".nii.gz", ".mha", ".mhd", ".nrrd"}


def _detect_format(path: str) -> str:
    """根据路径检测文件格式。"""
    if os.path.isdir(path):
        return "dicom_dir"
    lower = path.lower()
    if lower.endswith(".nii.gz"):
        return "nifti"
    _, ext = os.path.splitext(lower)
    if ext == ".dcm":
        return "dicom"
    if ext in (".nii",):
        return "nifti"
    if ext in (".mha", ".mhd"):
        return "metaimage"
    if ext == ".nrrd":
        return "nrrd"
    raise ValueError(f"不支持的文件格式: {ext}")


def _load_dicom_series(dir_path: str) -> sitk.Image:
    """加载 DICOM 序列目录。"""
    reader = sitk.ImageSeriesReader()
    dicom_files = reader.GetGDCMSeriesFileNames(dir_path)
    if not dicom_files:
        raise ValueError(f"在目录 {dir_path} 中未找到 DICOM 序列")
    reader.SetFileNames(dicom_files)
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()
    return reader.Execute()


def _load_dicom_file(file_path: str) -> sitk.Image:
    """加载单个 DICOM 文件。"""
    return sitk.ReadImage(file_path)


def _read_dicom_metadata(path: str) -> dict:
    """使用 pydicom 读取 DICOM 元数据。"""
    try:
        if os.path.isdir(path):
            files = [
                os.path.join(path, f)
                for f in os.listdir(path)
                if f.lower().endswith(".dcm")
            ]
            if files:
                ds = pydicom.dcmread(files[0], stop_before_pixels=True)
            else:
                return {}
        else:
            ds = pydicom.dcmread(path, stop_before_pixels=True)
        meta = {}
        for tag_name in [
            "PatientName", "PatientID", "StudyDescription",
            "SeriesDescription", "Modality", "StudyDate",
            "InstitutionName", "Manufacturer",
        ]:
            if hasattr(ds, tag_name):
                val = getattr(ds, tag_name)
                meta[tag_name] = str(val) if val else ""
        return meta
    except Exception:
        return {}


def load_image(path: str) -> ImageVolume:
    """加载医学图像，支持 DICOM/NIfTI/MHA/NRRD 格式。

    Args:
        path: 文件路径或 DICOM 目录路径。

    Returns:
        ImageVolume 对象。
    """
    fmt = _detect_format(path)

    if fmt == "dicom_dir":
        sitk_img = _load_dicom_series(path)
        metadata = _read_dicom_metadata(path)
    elif fmt == "dicom":
        sitk_img = _load_dicom_file(path)
        metadata = _read_dicom_metadata(path)
    else:
        sitk_img = sitk.ReadImage(path)
        metadata = {}

    # Convert to numpy array
    data = sitk.GetArrayFromImage(sitk_img)  # (Z, Y, X)
    data = np.transpose(data, (2, 1, 0))  # -> (X, Y, Z)

    spacing = sitk_img.GetSpacing()
    origin = sitk_img.GetOrigin()
    direction = sitk_img.GetDirection()

    return ImageVolume(
        data=data.astype(np.float32),
        spacing=spacing,
        origin=origin,
        direction=direction,
        metadata=metadata,
        file_path=path,
    )


def save_image(volume: ImageVolume, path: str):
    """保存图像到文件。

    Args:
        volume: ImageVolume 对象。
        path: 保存路径。
    """
    data = np.transpose(volume.data, (2, 1, 0))  # (X,Y,Z) -> (Z,Y,X)
    sitk_img = sitk.GetImageFromArray(data)
    sitk_img.SetSpacing(volume.spacing)
    sitk_img.SetOrigin(volume.origin)
    sitk_img.SetDirection(volume.direction)
    sitk.WriteImage(sitk_img, path)
