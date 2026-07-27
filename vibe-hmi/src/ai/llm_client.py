"""
LLM 客户端

支持两种接口格式：
1. OpenAI 兼容（/chat/completions）— GPT/通义/DeepSeek/Moonshot
2. Anthropic 兼容（/v1/messages）— 智谱 GLM (api/anthropic)

通过 base_url 自动判断接口类型：
- 包含 "/anthropic" → Anthropic 格式
- 其他 → OpenAI 格式
"""
import json
import requests


class LLMClient:
    """LLM 客户端（自动识别 OpenAI / Anthropic 接口）"""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        # 自动判断接口类型
        self._is_anthropic = "/anthropic" in self.base_url.lower()
        # 是否启用智谱 web_search（默认启用，测试连接时可关闭）
        self._enable_web_search = True

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """发送对话请求，返回标准化的响应 dict。

        返回格式（统一）:
          {"choices": [{"message": {"role":"assistant", "content": str, "tool_calls": [...]}}]}
        """
        if self._is_anthropic:
            return self._chat_anthropic(messages, tools)
        else:
            return self._chat_openai(messages, tools)

    def _chat_openai(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """OpenAI 兼容 /chat/completions"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict = {"model": self.model, "messages": messages}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        # 智谱 GLM：自动加原生 web_search（仅 OpenAI 兼容接口支持）
        is_zhipu = "bigmodel.cn" in self.base_url.lower()
        if is_zhipu and self._enable_web_search:
            web_search_tool = {
                "type": "web_search",
                "web_search": {
                    "enable": "True",
                    "search_engine": "search_std",
                    "search_result": "True",
                }
            }
            if "tools" not in body:
                body["tools"] = []
            body["tools"].insert(0, web_search_tool)

        resp = requests.post(url, json=body, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _chat_anthropic(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """Anthropic 兼容 /v1/messages

        将 OpenAI 格式的 messages + tools 转换为 Anthropic 格式，
        然后将 Anthropic 响应转换回 OpenAI 格式（统一外部接口）。
        """
        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        # 分离 system message
        system_text = ""
        user_assistant = []
        for msg in messages:
            if msg["role"] == "system":
                system_text += msg["content"] + "\n"
            else:
                user_assistant.append({"role": msg["role"], "content": msg["content"]})

        body: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": user_assistant,
        }
        if system_text.strip():
            body["system"] = system_text.strip()
        if tools:
            # 转换 OpenAI tools → Anthropic tools
            body["tools"] = [self._convert_tool_openai_to_anthropic(t) for t in tools]

        resp = requests.post(url, json=body, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()

        # 转换 Anthropic 响应 → OpenAI 格式
        return self._convert_anthropic_to_openai(data)

    def _convert_tool_openai_to_anthropic(self, tool: dict) -> dict:
        """OpenAI tool schema → Anthropic tool schema"""
        func = tool.get("function", tool)
        return {
            "name": func["name"],
            "description": func.get("description", ""),
            "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
        }

    def _convert_anthropic_to_openai(self, data: dict) -> dict:
        """Anthropic 响应 → OpenAI 格式"""
        content_blocks = data.get("content", [])
        text_content = ""
        tool_calls = []

        for block in content_blocks:
            if block.get("type") == "text":
                text_content += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                    },
                })

        message: dict = {"role": "assistant", "content": text_content}
        if tool_calls:
            message["tool_calls"] = tool_calls

        return {
            "choices": [{
                "message": message,
                "finish_reason": data.get("stop_reason", "stop"),
            }],
        }

    def send(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """发送对话，解析响应。

        返回:
          - {"type": "tool_call", "name": str, "args": dict, "tool_call_id": str, "assistant_msg": dict}
          - {"type": "text", "content": str, "assistant_msg": dict}
        """
        data = self.chat(messages, tools)
        choice = data["choices"][0]
        msg = choice["message"]

        if msg.get("tool_calls"):
            tc = msg["tool_calls"][0]
            func = tc["function"]
            return {
                "type": "tool_call",
                "name": func["name"],
                "args": json.loads(func["arguments"]),
                "tool_call_id": tc["id"],
                "assistant_msg": {"role": "assistant", "content": msg.get("content", ""), "tool_calls": msg["tool_calls"]},
            }

        return {
            "type": "text",
            "content": msg.get("content", ""),
            "assistant_msg": {"role": "assistant", "content": msg.get("content", "")},
        }

    def summarize(self, messages: list[dict]) -> dict:
        """工具结果回灌后，LLM 生成总结。"""
        data = self.chat(messages)
        choice = data["choices"][0]
        content = choice["message"].get("content", "")
        return {
            "type": "text",
            "content": content,
            "assistant_msg": {"role": "assistant", "content": content},
        }
