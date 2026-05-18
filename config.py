import os
import json
from dataclasses import dataclass

APP_NAME = "MedImager"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".medimager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "llm_provider": "openai",
    "openai_api_key": "",
    "openai_base_url": "https://api.openai.com/v1",
    "openai_model": "gpt-4o",
    "ollama_base_url": "http://localhost:11434",
    "ollama_model": "llama3",
    "custom_api_key": "",
    "custom_base_url": "",
    "custom_model": "",
    "custom_provider_name": "自定义",
    "last_open_dir": "",
    "window_geometry": None,
}

# 预设的 API 提供商
API_PRESETS = {
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "智谱 (Zhipu)": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-plus", "glm-4", "glm-4-flash"],
    },
    "硅基流动 (SiliconFlow)": {
        "base_url": "https://api.siliconflow.cn/v1",
        "models": ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3", "meta-llama/Meta-Llama-3.1-70B-Instruct"],
    },
    "Moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"],
    },
    "小米 MiMo": {
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
        "models": ["mimo-v2.5-pro", "mimo-v2.5", "mimo-v2-pro", "mimo-v2-omni", "mimo-v2.5-tts", "mimo-v2.5-tts-voiceclone", "mimo-v2.5-tts-voicedesign", "mimo-v2-tts"],
    },
    "Ollama (本地)": {
        "base_url": "http://localhost:11434",
        "models": ["llama3", "qwen2.5", "deepseek-r1"],
    },
}


@dataclass
class APIConfig:
    provider_name: str = "自定义"
    base_url: str = ""
    api_key: str = ""
    model: str = ""

    def is_valid(self) -> bool:
        return bool(self.base_url and self.model)

    @classmethod
    def from_dict(cls, cfg: dict) -> "APIConfig":
        return cls(
            provider_name=cfg.get("custom_provider_name", ""),
            base_url=cfg.get("custom_base_url", ""),
            api_key=cfg.get("custom_api_key", ""),
            model=cfg.get("custom_model", ""),
        )


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
