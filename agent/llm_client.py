import json
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """LLM 抽象接口。"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> dict | list:
        """发送对话请求。

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            tools: 工具定义列表（function calling 格式）
            stream: 是否流式返回

        Returns:
            响应字典，包含 content 和 tool_calls（如有）
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI API 客户端。"""

    def __init__(self, api_key: str, base_url: str, model: str):
        from openai import OpenAI
        base_url = base_url.rstrip("/")
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=60)
        self._model = model

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> dict | list:
        kwargs = {
            "model": self._model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        if stream:
            return self._client.chat.completions.create(stream=True, **kwargs)

        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as e:
            # 如果带 tools 调用失败（400 等），去掉 tools 重试
            if tools and ("400" in str(e) or "invalid" in str(e).lower()):
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                response = self._client.chat.completions.create(**kwargs)
            else:
                raise

        msg = response.choices[0].message
        result = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in msg.tool_calls
            ]
        return result


class OllamaClient(LLMClient):
    """Ollama API 客户端。"""

    def __init__(self, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._model = model

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> dict | list:
        import requests

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools

        resp = requests.post(
            f"{self._base_url}/api/chat",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        msg = data.get("message", {})
        result = {"role": "assistant", "content": msg.get("content", "")}
        if msg.get("tool_calls"):
            result["tool_calls"] = [
                {
                    "id": f"ollama_{i}",
                    "name": tc["function"]["name"],
                    "arguments": tc["function"].get("arguments", {}),
                }
                for i, tc in enumerate(msg["tool_calls"])
            ]
        return result


def create_client(
    provider: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> LLMClient:
    """创建 LLM 客户端。"""
    if provider == "openai":
        return OpenAIClient(api_key=api_key, base_url=base_url, model=model)
    elif provider == "ollama":
        return OllamaClient(base_url=base_url, model=model)
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")
