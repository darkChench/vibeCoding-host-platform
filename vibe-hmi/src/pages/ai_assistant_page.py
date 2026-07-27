"""
AI 助手页

对话 UI + 真实 LLM 调用（后台线程）+ function calling。
布局：单卡占满，对话历史区（可滚动）+ 输入区（多行 + 发送）。
"""
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QPlainTextEdit, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from .. import theme
from ..store import store
from ..ai.llm_worker import LLMWorker
from ..ai import ai_tools


class AIAssistantPage(QWidget):
    """AI 助手页"""

    def __init__(self):
        super().__init__()
        self._worker: LLMWorker | None = None
        self._thinking_timer: QTimer | None = None
        self._thinking_dots = 0
        self._build_ui()
        self._check_model_config()
        # 首次进入注入欢迎语
        if not store.ai_messages:
            self._add_bubble("assistant",
                "你好！我是 AI 运维助手。我可以帮你：\n\n"
                "* 📊 读取传感器数据 — \"读取温度\"、\"读取全部采样参数\"\n"
                "* 🔔 查询报警记录 — \"有哪些报警\"、\"未确认的报警\"\n"
                "* 📈 查看趋势数据 — \"温度趋势\"\n"
                "* 🔧 查看设备状态 — \"设备在线情况\"\n\n"
                "也可以问我其他问题，比如 Modbus 协议、设备参数含义等。\n\n"
                "请直接输入你的问题。"
            )

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._build_card(), 1)

    def _build_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # card-head
        head = QFrame()
        head.setObjectName("card-head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(10, 0, 10, 0)
        title = QLabel("✦ AI 运维助手")
        title.setObjectName("card-title")
        self.model_tag = QLabel("未配置模型")
        self.model_tag.setObjectName("tag")
        self.model_tag.setProperty("variant", "warn")
        self.model_tag.setFixedHeight(18)
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(self.model_tag, alignment=Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(head)

        # body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        # 对话历史区（可滚动）
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(14, 14, 14, 14)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()
        self.scroll.setWidget(self.messages_widget)
        bl.addWidget(self.scroll, 1)

        # 思考动画
        self.thinking_label = QLabel("● ● ●")
        self.thinking_label.setStyleSheet(
            f"color: {theme.HEX['MUTED']}; font-size: {theme.FS_MD}pt; padding: 4px 14px;"
        )
        self.thinking_label.setVisible(False)
        bl.addWidget(self.thinking_label)

        # 输入区
        input_frame = QFrame()
        input_frame.setObjectName("ai-input-bar")
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(10, 6, 10, 6)
        il.setSpacing(8)

        self.input_box = QPlainTextEdit()
        self.input_box.setObjectName("ai-input")
        self.input_box.setPlaceholderText("输入消息...（Ctrl+Enter 发送）")
        self.input_box.setFixedHeight(60)
        self.input_box.setStyleSheet(
            f"QPlainTextEdit#ai-input {{ border: 1px solid {theme.HEX['LINE_DARK']}; "
            f"border-radius: 8px; padding: 6px 10px; "
            f"background: #ffffff; font-size: {theme.FS_MD}pt; }}"
            f"QPlainTextEdit#ai-input:focus {{ border-color: {theme.HEX['PRIMARY']}; }}"
        )
        font = QFont()
        font.setPointSize(theme.FS_MD)
        self.input_box.setFont(font)

        self.btn_send = QPushButton("发送")
        self.btn_send.clicked.connect(self._on_send)
        self.input_box.keyPressEvent = self._on_key_press

        il.addWidget(self.input_box, 1)
        il.addWidget(self.btn_send, alignment=Qt.AlignmentFlag.AlignBottom)
        bl.addWidget(input_frame)

        cl.addWidget(body, 1)
        return card

    # ===== 消息气泡 =====

    def _add_bubble(self, role: str, text: str):
        """添加对话气泡（user 右对齐蓝底 / assistant 左对齐白底边框）"""
        bubble = QFrame()
        bubble.setObjectName(f"ai-bubble-{role}")
        bl = QVBoxLayout(bubble)
        bl.setContentsMargins(10, 8, 10, 8)
        bl.setSpacing(0)

        label = QLabel(text)
        label.setWordWrap(True)
        # 用户消息用纯文本，助手消息用 Markdown（支持表格/加粗/列表渲染）
        if role == "user":
            label.setTextFormat(Qt.TextFormat.PlainText)
        else:
            label.setTextFormat(Qt.TextFormat.MarkdownText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # 测量文本自然宽度，设置气泡的 sizeHint 宽度
        from PySide6.QtGui import QFontMetrics, QFont
        font = QFont()
        font.setPointSize(theme.FS_MD)
        fm = QFontMetrics(font)
        text_width = fm.horizontalAdvance(text)
        if role == "user":
            label.setStyleSheet(f"color: #ffffff; font-size: {theme.FS_MD}pt;")
            bubble.setStyleSheet(
                f"#ai-bubble-user {{ background: {theme.HEX['PRIMARY']}; border-radius: 8px; }}"
            )
            # 用户气泡：按内容宽度，最大 200px
            natural_width = min(text_width + 20, 200)
            bubble.setMaximumWidth(200)
            bubble.setMinimumWidth(0)
            label.setMaximumWidth(180)
        else:
            label.setStyleSheet(f"color: {theme.HEX['TEXT']}; font-size: {theme.FS_MD}pt;")
            bubble.setStyleSheet(
                f"#ai-bubble-assistant {{ background: #ffffff; border: 1px solid {theme.HEX['LINE']}; border-radius: 8px; }}"
            )

        bl.addWidget(label)

        # 插入到 stretch 之前
        row = QHBoxLayout()
        if role == "user":
            # 用户气泡：右侧对齐，不设 stretch 比例让气泡自适应宽度
            row.addStretch()
            row.addWidget(bubble)
        else:
            # 助手气泡：恢复原始比例（左侧，较宽）
            row.addWidget(bubble, 3)
            row.addStretch()
        if role == "assistant":
            bubble.setMaximumWidth(600)
        self.messages_layout.insertLayout(self.messages_layout.count() - 1, row)
        self._scroll_to_bottom()

    def _add_tool_card(self, name: str, args: dict, status: str = "running"):
        """添加工具调用卡片"""
        card = QFrame()
        card.setObjectName("ai-tool-card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.setSpacing(4)

        status_icon = {"running": "⏳", "done": "✓", "error": "✗"}.get(status, "⏳")
        status_color = {"running": theme.HEX["WARN"], "done": theme.HEX["OK"],
                        "error": theme.HEX["DANGER"]}.get(status, theme.HEX["WARN"])

        head = QLabel(f'<span style="color:{status_color};">{status_icon}</span> '
                      f'<b>{name}</b>')
        head.setTextFormat(Qt.TextFormat.RichText)
        head.setStyleSheet(f"font-size: {theme.FS_SM}pt; color: {theme.HEX['TEXT']};")
        cl.addWidget(head)

        args_str = json.dumps(args, ensure_ascii=False, indent=2)
        args_label = QLabel(f'<pre style="margin:0;color:{theme.HEX["MUTED"]};">{args_str}</pre>')
        args_label.setTextFormat(Qt.TextFormat.RichText)
        cl.addWidget(args_label)

        self._cur_tool_card = card
        self._cur_tool_head = head

        card.setStyleSheet(
            f"#ai-tool-card {{ background: {theme.HEX['TAG_BG']}; border-left: 3px solid {status_color}; "
            f"border-radius: 4px; margin: 2px 0; }}"
        )

        row = QHBoxLayout()
        row.addWidget(card, 5)
        row.addStretch()
        self.messages_layout.insertLayout(self.messages_layout.count() - 1, row)
        self._scroll_to_bottom()
        return card

    def _update_tool_card(self, status: str, summary: str):
        """更新最后一个工具卡片的状态"""
        if not hasattr(self, "_cur_tool_head"):
            return
        status_icon = {"running": "⏳", "done": "✓", "error": "✗"}.get(status, "⏳")
        status_color = {"running": theme.HEX["WARN"], "done": theme.HEX["OK"],
                        "error": theme.HEX["DANGER"]}.get(status, theme.HEX["WARN"])
        name = self._cur_tool_head.text()
        self._cur_tool_head.setText(f'<span style="color:{status_color};">{status_icon}</span> {name.split("</b>")[0].split("<b>")[-1] if "<b>" in name else name}')

        # 添加结果摘要
        result_label = QLabel(f'<span style="color:{theme.HEX["TEXT"]};">{summary}</span>')
        result_label.setTextFormat(Qt.TextFormat.RichText)
        result_label.setWordWrap(True)
        result_label.setStyleSheet(f"font-size: {theme.FS_SM}pt;")
        self._cur_tool_card.layout().addWidget(result_label)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    # ===== 思考动画 =====

    def _start_thinking(self):
        self.thinking_label.setVisible(True)
        self._thinking_dots = 0
        self._thinking_timer = QTimer()
        self._thinking_timer.timeout.connect(self._animate_thinking)
        self._thinking_timer.start(400)

    def _animate_thinking(self):
        self._thinking_dots = (self._thinking_dots + 1) % 4
        dots = "● " * self._thinking_dots + "○ " * (3 - self._thinking_dots)
        self.thinking_label.setText(f"AI 思考中 {dots.strip()}")

    def _stop_thinking(self):
        if self._thinking_timer:
            self._thinking_timer.stop()
            self._thinking_timer = None
        self.thinking_label.setVisible(False)

    # ===== 发送逻辑 =====

    def _on_key_press(self, event):
        """Ctrl+Enter 发送"""
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import QEvent
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._on_send()
        else:
            QPlainTextEdit.keyPressEvent(self.input_box, event)

    def _on_send(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return
        if not store.active_model_config():
            QMessageBox.warning(self, "未配置模型", "请先在模型配置页添加并启用 AI 模型")
            return

        self.input_box.clear()
        self._add_bubble("user", text)
        store.ai_messages.append({"role": "user", "content": text})
        self.btn_send.setEnabled(False)
        self._start_thinking()

        # 后台线程调 LLM
        self._worker = LLMWorker()
        self._worker.request_send(text)
        self._worker.finished_signal.connect(self._on_llm_response)
        self._worker.start()

    def _on_llm_response(self, data: dict):
        """LLM 响应回调"""
        self._stop_thinking()
        self.btn_send.setEnabled(True)

        if data.get("error"):
            self._add_bubble("assistant", f"⚠ 出错了：{data['error']}")
            return

        result = data.get("result", {})
        mode = data.get("mode", "send")

        if mode == "send":
            if result.get("type") == "tool_call":
                # 工具调用
                name = result["name"]
                args = result["args"]
                self._add_tool_card(name, args, "running")

                # 执行工具
                tool_result = ai_tools.call(name, args)
                status = "done" if tool_result["ok"] else "error"
                self._update_tool_card(status, tool_result.get("summary", ""))

                # 二次调 LLM 总结
                self._start_thinking()
                self._worker = LLMWorker()
                self._worker.request_summarize(name, tool_result)
                self._worker.finished_signal.connect(self._on_llm_response)
                self._worker.start()
            else:
                # 纯文本回复
                content = result.get("content", "")
                self._add_bubble("assistant", content)
                store.ai_messages.append({"role": "assistant", "content": content})

        elif mode == "summarize":
            content = result.get("content", "")
            self._add_bubble("assistant", content)
            store.ai_messages.append({"role": "assistant", "content": content})

    # ===== 模型配置状态 =====

    def _check_model_config(self):
        """检查模型配置状态，更新 tag"""
        active = store.active_model_config()
        if active:
            self.model_tag.setText(f"{active['provider']} · {active['model']}")
            self.model_tag.setProperty("variant", "ok")
            self.input_box.setEnabled(True)
            self.btn_send.setEnabled(True)
        else:
            self.model_tag.setText("未配置模型")
            self.model_tag.setProperty("variant", "warn")
            self.input_box.setEnabled(False)
            self.btn_send.setEnabled(False)
        self.model_tag.style().polish(self.model_tag)

    def showEvent(self, event):
        """每次进入页面刷新模型配置状态"""
        super().showEvent(event)
        self._check_model_config()
