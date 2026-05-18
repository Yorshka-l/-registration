import json
import re
from agent.llm_client import LLMClient
from agent.tools import AGENT_TOOLS


SYSTEM_PROMPT = """\
你是一个医学图像处理 AI 助手，嵌入在 MedImager 桌面软件中。

你可以执行以下操作：
1. 加载医学图像（DICOM/NIfTI/MHA/NRRD）
2. 调整窗宽窗位，应用预设
3. 跳转切片
4. 执行图像分割（PyTorch 模型）
5. 执行 SyNRA 配准（CT-to-RTCT 可变形配准）
6. 执行多模态配准（MRI↔PET 配准）

===== CT-to-RTCT 配准流程 =====

用户说"CT配准"或"RTCT配准"时，按以下步骤操作：

第1步：用 get_current_directory 获取当前目录
第2步：用 list_directory_files 列出目录下的文件
第3步：根据文件名判断角色：
  - 文件名含 "RTCT" 或 "rtct" → 这是固定图像 (fixed)，即放疗计划CT
  - 文件名含 "CT" 但不含 "RTCT" → 这是待配准图像 (moving)
  - 文件名含 "PET" 或 "pet" → PET图像（可选）
  - 文件名含 "mask" 或 "ROI" 或 "roi" → 掩码（可选）
  - 如果文件名不清楚，询问用户
第4步：用 load_image 加载这些文件
第5步：用 set_reg_files 设置配准文件
第6步：用 set_reg_param 设置参数（通常用默认即可）
第7步：用 run_registration 执行配准

===== 多模态配准流程（MRI↔PET）=====

用户说"MRI配准"、"PET配准"、"MRI到PET"、"PET到MRI"时，按以下步骤操作：

第1步：用 get_current_directory 获取当前目录
第2步：用 list_directory_files 列出目录下的文件
第3步：根据文件名识别 MRI 和 PET 文件：
  - 文件名含 "mri" 或 "MRI" 或 "t1" 或 "T1" → MRI 文件
  - 文件名含 "pet" 或 "PET" → PET 文件
  - 如果文件名不清楚，询问用户
第4步：判断配准模式：
  - 用户说"将MRI配准到PET"或"MRI→PET" → mode="mri_to_pet"
  - 用户说"将PET配准到MRI"或"PET→MRI" → mode="pet_to_mri"
  - 如果用户没明确说，默认根据常用场景判断或询问用户
第5步：用 run_multimodal_registration 执行配准，例如：
  {"mode": "mri_to_pet", "mri_path": "D:/data/MRI.nii.gz", "pet_path": "D:/data/PET.nii.gz"}
  或
  {"mode": "pet_to_mri", "mri_path": "D:/data/MRI.nii.gz", "pet_path": "D:/data/PET.nii.gz"}

多模态配准会自动处理：
  - PET 重采样到 512x512x36（MRI→PET模式）
  - MRI 重采样到 512x512（PET→MRI模式）
  - MRI 方向修正（翻转负方向轴）
  - SyNRA 可变形配准
  - 保持原始数据类型

===== 配准参数说明 =====
- selected_window: CT窗位预处理部位，常用值：
  Lung（肺部）、Thorax（胸腔）、Abdomen（腹部）、Pelvis（盆腔）、Brain（脑部）
- flow_sigma / total_sigma: 变形场平滑度，0.3-1.0，越大越平滑
- 如果用户没有指定参数，使用默认值即可
- 如果配准结果有奇怪的变形，增大 flow_sigma 和 total_sigma
- 如果配准精度不够，增加 reg_iterations 或减小 sigma

请根据用户的自然语言描述，智能调整参数并执行操作。回复使用中文。

当需要调用工具时，请使用以下 JSON 格式输出（单独一行，不要包裹在其他文本中）：
```json
{"name": "工具名", "arguments": {"参数1": "值1", "参数2": "值2"}}
```
可以一次输出多个工具调用，每个用单独的 JSON 块。\
"""


class AgentController:
    """Agent 控制器，负责将用户意图解析为工具调用。"""

    def __init__(self, llm_client: LLMClient):
        self._client = llm_client
        self._messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self._tool_handlers: dict[str, callable] = {}

    def register_tool(self, name: str, handler: callable):
        self._tool_handlers[name] = handler

    def chat(self, user_message: str) -> str:
        self._messages.append({"role": "user", "content": user_message})

        try:
            response = self._client.chat(
                messages=self._messages,
                tools=AGENT_TOOLS,
            )
        except Exception as e:
            print(f"[Agent] 首次调用失败: {e}，尝试不带 tools 重试")
            try:
                response = self._client.chat(messages=self._messages, tools=None)
            except Exception as e2:
                return f"API 调用失败: {e2}"

        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        # 最多执行 3 轮工具调用，防止死循环
        max_rounds = 3
        round_count = 0

        # 如果 API 没有返回 tool_calls，尝试从文本中解析
        if not tool_calls:
            tool_calls = self._parse_tool_calls_from_text(content)

        if tool_calls:
            results = []
            for call in tool_calls:
                tool_name = call["name"]
                tool_args = call.get("arguments", {})
                result = self._execute_tool(tool_name, tool_args)
                results.append(f"[{tool_name}] {result}")

            tool_results_msg = "\n".join(results)
            self._messages.append({
                "role": "assistant",
                "content": content or f"已执行: {tool_results_msg}",
            })
            self._messages.append({
                "role": "user",
                "content": f"工具执行结果:\n{tool_results_msg}\n请总结执行结果。",
            })

            followup = self._client.chat(
                messages=self._messages,
                tools=None,
            )
            content = followup.get("content", tool_results_msg)

        self._messages.append({"role": "assistant", "content": content})
        return content

    def _parse_tool_calls_from_text(self, text: str) -> list[dict]:
        """从模型文本输出中解析工具调用 JSON。"""
        calls = []
        # 匹配 ```json ... ``` 或 { "name": ..., "arguments": ... } 模式
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'(\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{.*?\}\s*\})',
        ]
        for pattern in patterns:
            for match in re.findall(pattern, text, re.DOTALL):
                try:
                    obj = json.loads(match)
                    if isinstance(obj, dict) and "name" in obj:
                        calls.append({
                            "name": obj["name"],
                            "arguments": obj.get("arguments", {}),
                        })
                    elif isinstance(obj, list):
                        for item in obj:
                            if isinstance(item, dict) and "name" in item:
                                calls.append({
                                    "name": item["name"],
                                    "arguments": item.get("arguments", {}),
                                })
                except json.JSONDecodeError:
                    continue
        return calls

    def _execute_tool(self, name: str, args: dict) -> str:
        if name in self._tool_handlers:
            try:
                return self._tool_handlers[name](args)
            except Exception as e:
                return f"执行失败: {e}"
        return f"未知工具: {name}"

    def clear_history(self):
        self._messages = [{"role": "system", "content": SYSTEM_PROMPT}]
