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
        self._last_user_question = ""  # 记住用户最近一次的问题，供 summarize 时引用
        self._running = True

    def stop(self):
        self._running = False
        self.quit()
        self.wait(2000)

    def request_send(self, user_text: str):
        """准备发送模式"""
        self._mode = "send"
        self._user_text = user_text
        self._last_user_question = user_text  # 记下用户的问题

    def request_summarize(self, tool_name: str, tool_result: dict, user_question: str = ""):
        """准备总结模式。

        Args:
            tool_name: 工具名
            tool_result: 工具返回结果
            user_question: 用户最初的问题（用于让 LLM 针对该问题作答，而非泛泛复述数据）。
                           若调用方未传，则回退到内部记录的最近一次问题。
        """
        self._mode = "summarize"
        self._tool_name = tool_name
        self._tool_result = tool_result
        if user_question:
            self._last_user_question = user_question

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
                    f"当前时间：{now}。可以读取传感器/查报警/看趋势/查设备状态/查询历史数据库，也可以回答通用问题。"
                    f"\n\n设备数据说明："
                    f"\n- 密度单位是 MPa，在表压工况下出现负值是正常现象（负表压），不要将其视为异常。"
                    f"\n- 各传感器的单位和量程以参数配置为准，不要对单位是否合理做主观判断。"
                    f"\n- 读取数据后直接如实报告数值和单位即可。"
                    f"\n\n能力说明："
                    f"\n- 查历史数据总数、时间范围、按时间段统计 → 用 query_history 工具"
                    f"\n- 取最近趋势做分析（均值/方差/标准差等）→ 用 get_trend 或 query_history"
                    f"\n- 不要告诉用户'无法查询数据库'，你有 query_history 工具可以直接查。"
                    f"\n- 当用户提到时间范围（如'一天/最近24小时/一周/近1小时'），"
                    f"请换算成具体的 start_time（基于当前时间 {now} 往前推算），"
                    f"格式 YYYY-MM-DD HH:MM:SS，传给 query_history 的 start_time 参数。"
                    f"工具会等间隔抽样覆盖整个范围，分析的是该时段的整体趋势，而非最近几个点。"
                    f"\n\n输出格式要求："
                    f"\n- 禁止使用 LaTeX 公式语法（不要出现 $、$$、\\sigma、\\mu、\\frac、\\sqrt 等），"
                    f"界面不支持渲染。"
                    f"\n- 数学公式用纯文本 + Unicode 符号书写，例如：σ² = 0.00044、√0.00044 ≈ 0.021、"
                    f"均值 μ ≈ 29.60、(29.62 - 29.60)² 等。"
                )}]
                messages.extend(store.ai_messages)
                messages.append({"role": "user", "content": self._user_text})

                result = client.send(messages, ai_tools.TOOLS)
                self.finished_signal.emit({"mode": "send", "result": result})

            elif self._mode == "summarize":
                # 构建简洁 messages（只传 system + 工具结果，不传完整历史避免兼容性问题）
                messages = [{"role": "system", "content": (
                    "你是工业设备运维助手，擅长数据分析。"
                    "下面会提供工具返回的数据，包括【统计量】和【趋势序列】。\n"
                    "重要：所有统计量（均值、方差、标准差、极值）已由系统基于全部数据点精确计算，"
                    "你只需直接引用这些数字作答，严禁自行重新计算（你的数值计算不准确）。\n"
                    "用户问方差/标准差/均值等时，直接报工具给的统计值即可；"
                    "用户问趋势时，结合统计量和序列走势描述。用简洁中文回复。"
                    "\n\n输出格式要求：禁止使用 LaTeX 公式语法（不要出现 $、$$、\\sigma、\\mu、\\frac、\\sqrt 等），"
                    "界面不支持渲染。数学公式用纯文本 + Unicode 符号书写，"
                    "例如：σ² = 0.00044、σ = 0.021 ℃、均值 μ = 29.60 等。"
                )}]
                # 追加工具结果（用 user 角色包装，兼容 Anthropic 接口）
                tool_summary = self._tool_result.get("summary", "")
                # 明确告诉 LLM 用户的问题，让它针对问题作答而非复述数据
                user_q = self._last_user_question or ""
                prompt = f"用户的问题：{user_q}\n\n工具 {self._tool_name} 返回的数据：\n{tool_summary}\n\n请针对用户的问题，基于以上数据进行分析和计算后回复。"
                messages.append({"role": "user", "content": prompt})

                result = client.summarize(messages)
                self.finished_signal.emit({"mode": "summarize", "result": result})

        except Exception as e:
            self.finished_signal.emit({"mode": self._mode, "error": str(e)})
