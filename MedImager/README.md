# MedImager

基于 PySide6 的医学图像处理桌面平台，集成影像查看、配准、分割与 AI Agent 对话功能。

## 功能概览

### 影像查看
- 支持 DICOM (.dcm / 目录)、NIfTI (.nii / .nii.gz)、MetaImage (.mha / .mhd)、NRRD (.nrrd) 格式
- 三轴面同步显示（轴状面 / 冠状面 / 矢状面），基于 pyqtgraph 高性能渲染
- 窗宽窗位滑块调节，内置软组织、肺、骨、脑、肝脏、PET SUV 等预设
- 多种色表切换（灰度、热力图、反转灰度等）

### 图像配准
- **SyNRA 配准**: 基于 ANTs 的 CT-to-RTCT 可变形配准，支持仿射 + SyN 两阶段参数全量自定义、Z 轴分段窗位、掩码约束
- **多模态配准**: MRI <-> PET 配准，自动处理重采样（PET 512x512x36 / MRI 512x512）与方向修正
- 所有配准任务在后台线程异步执行，不阻塞 UI

### 图像分割
- 加载 PyTorch .pth 模型进行 3D 体数据推理
- 支持 CPU / CUDA 自动切换，二值化阈值可调

### AI Agent
- 自然语言指令驱动，通过对话完成图像加载、窗宽调节、配准等操作
- 内置工具调用框架，Agent 可直接操控 UI 和执行配准流程
- 支持多种 LLM API 提供商，内置预设一键切换：

| 提供商 | 示例模型 |
|--------|---------|
| OpenAI | gpt-4o, gpt-4o-mini |
| DeepSeek | deepseek-chat, deepseek-reasoner |
| 智谱 (Zhipu) | glm-4-plus, glm-4-flash |
| 硅基流动 (SiliconFlow) | Qwen2.5-72B, DeepSeek-V3 |
| Moonshot | moonshot-v1-128k |
| 小米 MiMo | mimo-v2.5-pro |
| Ollama (本地) | llama3, qwen2.5, deepseek-r1 |
| 自定义 | 任意 OpenAI 兼容 API |

## 安装

```bash
pip install -r requirements.txt
```

如需使用配准功能，还需安装 ANTs：

```bash
pip install antspyx
```

### 依赖说明

| 包名 | 版本 | 用途 |
|------|------|------|
| PySide6 | 6.8.3 | Qt GUI 框架（勿用 6.11.0，有 DLL 兼容问题） |
| pyqtgraph | >=0.13.0 | 高性能科学图像显示 |
| numpy | >=1.24.0 | 数值计算 |
| pydicom | >=2.4.0 | DICOM 文件读取与元数据解析 |
| SimpleITK | >=2.3.0 | 多格式医学影像加载与重采样 |
| torch | >=2.0.0 | PyTorch，用于分割模型推理 |
| openai | >=1.0.0 | OpenAI 兼容 API 客户端 |
| requests | >=2.31.0 | HTTP 请求（Ollama 等） |
| antspyx | - | ANTs 配准引擎（可选，配准功能必需） |

## 运行

```bash
python main.py
```

## 项目结构

```python
MedImager/
├── main.py                         # 应用入口，初始化服务与窗口
├── config.py                       # 配置管理、API 提供商预设
├── requirements.txt
├── assets/
│   └── style.qss                   # 深色主题 QSS 样式表
├── ui/
│   ├── main_window.py              # 主窗口（菜单栏、工具栏、停靠面板布局）
│   ├── image_viewer.py             # 三轴面图像查看器（pyqtgraph）
│   ├── dicom_browser.py            # 文件浏览器
│   ├── registration_panel.py       # 配准操作面板
│   ├── segmentation_panel.py       # 分割操作面板
│   ├── agent_panel.py              # AI Agent 对话面板 + API 设置
│   └── styles/
│       ├── tokens.py               # 设计令牌（颜色、字体）
│       └── components.py           # 可复用 UI 组件
├── core/
│   ├── image_io.py                 # 多格式图像加载（SimpleITK + pydicom）
│   ├── image_volume.py             # ImageVolume 数据类
│   ├── registration.py             # SyNRA 配准 + 多模态配准（ANTs 封装）
│   └── segmentation.py             # PyTorch 分割推理
├── services/
│   ├── image_service.py            # 图像加载服务
│   ├── registration_service.py     # 配准服务
│   ├── segmentation_service.py     # 分割服务
│   ├── agent_service.py            # Agent 服务
│   └── worker_manager.py           # QThread Worker 统一生命周期管理
├── state/
│   ├── app_state.py                # 全局应用状态（信号/槽）
│   └── image_state.py              # 图像状态管理
└── agent/
    ├── llm_client.py               # LLM 客户端（OpenAI / Ollama 双协议）
    ├── tools.py                    # Agent 可调用工具定义（14 个工具）
    └── agent_controller.py         # Agent 控制器（意图解析 + 工具调用 + 多轮对话）
```

## 架构

应用采用 **Service-State-UI** 三层架构：

- **State**: `AppState` / `ImageState` 通过 Qt Signal 广播状态变更，各面板订阅响应
- **Service**: `ImageService`、`RegistrationService`、`SegmentationService`、`AgentService` 封装业务逻辑
- **WorkerManager**: 统一管理 QThread 后台任务，支持命名任务、自动清理、日志回传
- **Agent**: `AgentController` 接收自然语言输入，调用 LLM 解析意图，通过注册的工具函数操控 UI 和执行操作

## 配置

配置文件保存在 `~/.medimager/config.json`，包含：
- LLM 提供商与 API Key
- 上次打开的目录
- 窗口几何信息

AI Agent 的 API 设置也可在界面底部的 Agent 面板中直接修改。
