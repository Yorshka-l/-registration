"""Agent 服务 — LLM 对话 + 工具注册表。"""

import os
import threading
from PySide6.QtCore import QTimer

from agent.agent_controller import AgentController
from agent.llm_client import OpenAIClient, OllamaClient
from agent.tools import AGENT_TOOLS, WINDOW_PRESETS
from config import load_config, APIConfig


class ToolRegistry:
    """Agent 工具注册表 — 管理所有可调用工具。"""

    def __init__(self):
        self._handlers: dict[str, callable] = {}

    def register(self, name: str, handler: callable):
        self._handlers[name] = handler

    def execute(self, name: str, args: dict) -> str:
        handler = self._handlers.get(name)
        if not handler:
            return f"未知工具: {name}"
        try:
            return handler(args)
        except Exception as e:
            return f"执行失败: {e}"

    def get_all_names(self) -> list[str]:
        return list(self._handlers.keys())


class AgentService:
    """Agent 对话服务。"""

    def __init__(self):
        self._controller: AgentController | None = None
        self._tool_registry = ToolRegistry()

    @property
    def tools(self) -> ToolRegistry:
        return self._tool_registry

    def get_or_create_controller(self) -> AgentController:
        if self._controller is not None:
            return self._controller

        cfg = load_config()
        api_cfg = APIConfig.from_dict(cfg)

        if not api_cfg.is_valid():
            raise ValueError(
                "请先点击 Agent 面板的「设置」按钮配置 API\n"
                "支持 OpenAI、DeepSeek、智谱、硅基流动等 OpenAI 兼容接口"
            )

        if "ollama" in api_cfg.provider_name.lower() or "localhost:11434" in api_cfg.base_url:
            client = OllamaClient(base_url=api_cfg.base_url, model=api_cfg.model)
        else:
            client = OpenAIClient(api_key=api_cfg.api_key, base_url=api_cfg.base_url, model=api_cfg.model)

        ctrl = AgentController(client)
        # 将注册的工具绑定到 controller
        for name in self._tool_registry.get_all_names():
            ctrl.register_tool(name, lambda args, n=name: self._tool_registry.execute(n, args))

        self._controller = ctrl
        return ctrl

    def chat(self, message: str) -> str:
        ctrl = self.get_or_create_controller()
        return ctrl.chat(message) or "（无回复）"

    def clear_history(self):
        if self._controller:
            self._controller.clear_history()

    def reset(self):
        self._controller = None
