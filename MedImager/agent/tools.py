"""Agent 可调用工具的注册表。"""

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "load_image",
            "description": "加载医学图像文件。支持 DICOM (.dcm)、NIfTI (.nii/.nii.gz)、MetaImage (.mha/.mhd)、NRRD (.nrrd) 格式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "图像文件或目录的路径"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_window_level",
            "description": "设置图像显示的窗宽和窗位。",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_width": {"type": "integer", "description": "窗宽值"},
                    "window_level": {"type": "integer", "description": "窗位值"},
                },
                "required": ["window_width", "window_level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_slice",
            "description": "设置当前显示的切片编号。",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "切片编号（从 0 开始）"}
                },
                "required": ["index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_segmentation",
            "description": "使用指定的 PyTorch 模型对当前图像执行分割。",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_path": {"type": "string", "description": "PyTorch .pth 模型文件路径"},
                    "threshold": {"type": "number", "description": "分割阈值，默认 0.5"},
                },
                "required": ["model_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_image_info",
            "description": "获取当前加载图像的基本信息（尺寸、模态、间距等）。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_preset",
            "description": "应用预设的窗宽窗位组合。",
            "parameters": {
                "type": "object",
                "properties": {
                    "preset": {
                        "type": "string",
                        "enum": ["soft_tissue", "lung", "bone", "brain", "liver"],
                        "description": "预设名称",
                    }
                },
                "required": ["preset"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reg_files",
            "description": "设置 SyNRA 配准的输入文件路径。fixed=固定图像(RTCT)，moving=待配准图像(CT)，pet=PET图像(可选)，mask=掩码(可选)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "fixed": {"type": "string", "description": "固定图像路径 (RTCT)"},
                    "moving": {"type": "string", "description": "待配准图像路径 (CT)"},
                    "pet": {"type": "string", "description": "PET 图像路径 (可选)"},
                    "mask": {"type": "string", "description": "掩码文件路径 (可选)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reg_param",
            "description": (
                "调整 SyNRA 配准参数。可调参数包括：\n"
                "selected_window: CT窗位预处理部位 (Abdomen/Brain/Skull/Extremities/Liver/Lung/Pelvis/SkullBase/SpineA/SpineB/Thorax, 或 null 表示仅空气截断)\n"
                "aff_metric: 仿射度量 (mattes/meansquares/gc)\n"
                "aff_sampling: 仿射直方图bin数\n"
                "aff_iterations: 仿射各层迭代次数数组\n"
                "aff_shrink_factors: 仿射缩放因子数组\n"
                "aff_smoothing_sigmas: 仿射平滑sigma数组\n"
                "syn_metric: SyN度量 (mattes/meansquares/gc)\n"
                "syn_sampling: SyN直方图bin数\n"
                "flow_sigma: 流动场平滑度 (越大越平滑，减少伪影)\n"
                "total_sigma: 总场平滑度 (越大越平滑)\n"
                "reg_iterations: SyN各层迭代次数数组"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "selected_window": {
                        "type": "string",
                        "enum": ["Abdomen", "Brain", "Skull", "Extremities", "Liver", "Lung",
                                 "Pelvis", "SkullBase", "SpineA", "SpineB", "Thorax"],
                        "description": "CT窗位预处理部位，用于HU值截断"
                    },
                    "aff_metric": {"type": "string", "enum": ["mattes", "meansquares", "gc"]},
                    "aff_sampling": {"type": "integer", "description": "仿射阶段直方图bin数"},
                    "aff_iterations": {"type": "array", "items": {"type": "integer"}, "description": "仿射各层迭代次数"},
                    "aff_shrink_factors": {"type": "array", "items": {"type": "integer"}},
                    "aff_smoothing_sigmas": {"type": "array", "items": {"type": "integer"}},
                    "syn_metric": {"type": "string", "enum": ["mattes", "meansquares", "gc"]},
                    "syn_sampling": {"type": "integer"},
                    "flow_sigma": {"type": "number", "description": "流动场sigma，越大越平滑，减少配准伪影但可能降低精度"},
                    "total_sigma": {"type": "number", "description": "总场sigma"},
                    "reg_iterations": {"type": "array", "items": {"type": "integer"}, "description": "SyN各层迭代次数"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_registration",
            "description": "使用当前设置的文件和参数执行 SyNRA 配准。调用前请先用 set_reg_files 设置文件、set_reg_param 设置参数。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_loaded_images",
            "description": "列出当前已加载的所有图像文件及其路径和模态信息。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_directory",
            "description": "获取左侧文件浏览器当前打开的目录路径。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory_files",
            "description": "列出左侧文件浏览器当前目录下的所有医学影像文件（DICOM/NIfTI/MHA/NRRD）和子目录。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_multimodal_registration",
            "description": (
                "执行多模态配准（MRI↔PET）。支持两种模式：\n"
                "1. mri_to_pet: 将 MRI 配准到 PET 空间，PET 会被重采样到 512x512x36 作为固定像\n"
                "2. pet_to_mri: 将 PET 配准到 MRI 空间，MRI 会被重采样到 512x512 作为固定像\n\n"
                "自动处理：PET 重采样、MRI 重采样、方向修正、SyNRA 配准。\n"
                "输出文件保存到 mri_path 所在目录。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["mri_to_pet", "pet_to_mri"],
                        "description": "配准模式：mri_to_pet 将 MRI 配准到 PET 空间，pet_to_mri 将 PET 配准到 MRI 空间"
                    },
                    "mri_path": {"type": "string", "description": "MRI 文件路径"},
                    "pet_path": {"type": "string", "description": "PET 文件路径"},
                },
                "required": ["mode", "mri_path", "pet_path"],
            },
        },
    },
]

# Preset mapping
WINDOW_PRESETS = {
    "soft_tissue": (400, 40),
    "lung": (1500, -600),
    "bone": (2000, 300),
    "brain": (80, 40),
    "liver": (150, 30),
}
