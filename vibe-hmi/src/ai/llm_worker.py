"""
LLM 后台线程

在后台线程调 LLM API，避免 UI 卡顿。
两种模式：send（用户消息 → LLM 响应）、summarize（工具结果 → LLM 总结）。
"""
from PySide6.QtCore import QThread, Signal

from .llm_client import LLMClient
from . import ai_tools
from ..store import store


class LLMWorker(QThread):
    """LLM 后台请求线程"""

    # 请求完成信号：{"mode": "send"/"summarize", "result": dict, "error": str|None}
    finished_signal = Signal(dict)

    def __init__(self):
        super().__init__()
        self._mode = "send"  # "send" or "summarize"
        self._user_text = ""
        self._tool_name = ""
        self._tool_result = None
        self._running = True

    def stop(self):
        self._running = False
        self.quit()
        self.wait(2000)

    def request_send(self, user_text: str):
        """准备发送模式"""
        self._mode = "send"
        self._user_text = user_text

    def request_summarize(self, tool_name: str, tool_result: dict):
        """准备总结模式"""
        self._mode = "summarize"
        self._tool_name = tool_name
        self._tool_result = tool_result

    def run(self):
        cfg = store.active_model_config()
        if not cfg:
            self.finished_signal.emit({"mode": self._mode, "error": "未配置 AI 模型"})
            return

        client = LLMClient(cfg["base_url"], cfg["api_key"], cfg["model"])

        try:
            if self._mode == "send":
                # 构建消息（对话历史 + 新消息）
                from datetime import datetime
                now = datetime.now().strftime("%Y年%m月%d日 %H:%M")
                provider = cfg.get("provider", "")
                model_name = cfg.get("model", "")
                messages = [{"role": "system", "content": (
                    f"你是{provider} {model_name}，运行在工业设备上位机中。"
                    f"当前时间：{now}。可以读取传感器/查报警/看趋势/查设备状态，也可以回答通用问题。"
                    f"\n\n设备数据说明："
                    f"\n- 密度单位是 MPa，在表压工况下出现负值是正常现象（负表压），不要将其视为异常。"
                    f"\n- 各传感器的单位和量程以参数配置为准，不要对单位是否合理做主观判断。"
                    f"\n- 读取数据后直接如实报告数值和单位即可。"
                )}]
                messages.extend(store.ai_messages)
                messages.append({"role": "user", "content": self._user_text})

                result = client.send(messages, ai_tools.TOOLS)
                self.finished_signal.emit({"mode": "send", "result": result})

            elif self._mode == "summarize":
                # 构建简洁 messages（只传 system + 工具结果，不传完整历史避免兼容性问题）
                messages = [{"role": "system", "content": (
                    "你是工业设备运维助手。根据工具返回的数据，用简洁中文回复用户。"
                    "如果有多个参数，请全部列出。"
                )}]
                # 追加工具结果（用 user 角色包装，兼容 Anthropic 接口）
                tool_summary = self._tool_result.get("summary", "")
                messages.append({
                    "role": "user",
                    "content": f"工具 {self._tool_name} 返回结果：\n{tool_summary}\n\n请根据以上数据回复用户。",
                })

                result = client.summarize(messages)
                self.finished_signal.emit({"mode": "summarize", "result": result})

        except Exception as e:
            self.finished_signal.emit({"mode": self._mode, "error": str(e)})
