"""
串口连接页

迁移自原型 js/pages/serial.js + js/components/console.js。
布局：console（三行 grid：console-tabs / terminal / sendbar）。

终端：等宽字体，报文行整行按方向着色（TX 蓝 / RX 绿，不显示行首标签），时间戳。
手动发送：HEX/ASCII 切换、行结束符追加、自动发送定时、发送历史。
协议层自动收发的 TX/RX 报文也注入终端（通过 log_callback）。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QPlainTextEdit, QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtGui import QTextCharFormat, QTextCursor, QColor, QFont
from collections.abc import Callable
import os
import time
from datetime import datetime

from .. import theme
from .. import dialogs
from ..store import store
from .. import paths
from ..serial.serial_manager import serial_manager

# 日志文件保存目录（开发模式=项目根/history,打包模式=exe 同级/history）
HISTORY_DIR = os.path.join(paths.app_root(), "history")
# 日志大小阈值（10MB），超过自动保存为 txt
LOG_SIZE_THRESHOLD = 10 * 1024 * 1024
# 终端最多保留的行数（防内存膨胀）；更早的行只留在 _lines 里供保存
TERMINAL_MAX_LINES = 5000
# 终端正文色 / 时间戳色
TEXT_COLOR = "#17202c"
TIMESTAMP_COLOR = "#0b6fb3"
# ASCII 显示时 \r\n 对应的块内换行符：Qt 文本版面把它当作强制换行，不需要经过 HTML
ASCII_LINE_BREAK = "\u2028"
# 一行日志的显示定义：[(文本, 颜色, 是否加粗), ...]
Segments = list[tuple[str, str, bool]]


def _now_hms() -> str:
    """当前日期时间 YYYY-MM-DD HH:MM:SS.mmm"""
    now = datetime.now()
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')}.{now.microsecond // 1000:03d}"


def _bytes_to_hex(data: bytes) -> str:
    """bytes → "01 03 08 ..." 格式"""
    return " ".join(f"{b:02X}" for b in data)


def _parse_hex(text: str) -> list[int] | None:
    """解析 HEX 字符串 → list[int]，非法返回 None"""
    cleaned = text.replace(" ", "").replace(",", "")
    if len(cleaned) % 2 != 0:
        return None
    try:
        return [int(cleaned[i:i+2], 16) for i in range(0, len(cleaned), 2)]
    except ValueError:
        return None


def _ascii_to_bytes(text: str) -> list[int]:
    """ASCII 字符串 → list[int]"""
    return list(text.encode("ascii", errors="replace"))


# 字节 → ASCII 显示字符：可打印字符原样，\r 和 \n 变成块内换行，其余显示为 .
_ASCII_DISPLAY = {
    b: (chr(b) if 32 <= b < 127 else (ASCII_LINE_BREAK if b in (0x0D, 0x0A) else "."))
    for b in range(256)
}


def _hex_to_ascii(hex_str: str) -> str:
    """HEX 字符串 → ASCII 文本（不可打印字符显示为 .，\\r\\n 转为块内换行符）。

    \\r\\n 算一个换行，单独的 \\r 或 \\n 各算一个。整帧一次转换完，不逐字节循环：
    整体重绘几千行时，这一步的耗时是大头。
    """
    try:
        text = bytes.fromhex(hex_str.replace(" ", "")).decode("latin-1")
    except ValueError:
        return hex_str  # 不是合法 HEX 帧：按原样显示
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.translate(_ASCII_DISPLAY)


# 行结束符映射（显示符号 → 实际字节）
LINE_ENDINGS = {
    "无": b"",
    "\\r": b"\r",
    "\\n": b"\n",
    "\\r\\n": b"\r\n",
}


class SerialPage(QWidget):
    """串口连接页：控制台 + 终端 + 手动发送"""

    # 类级日志回调（供协议层注入 TX/RX 行）
    # 不用实例属性，因为 PollWorker 的 protocol 在后台线程创建，
    # 需要一个全局可访问的入口
    _instance: "SerialPage | None" = None

    def __init__(self):
        super().__init__()
        SerialPage._instance = self
        # 协议日志桥：worker 线程 emit → 主线程 queued → append_line。
        # 必须经信号投递：QTextDocument 不是线程安全的，worker 线程直接
        # appendHtml 会跨线程创建 QObject 子项（堆损坏 → 随机卡死/崩溃）
        _protocol_log_bridge.line.connect(self.append_line)
        self._current_tab = "raw"  # raw / stats / diagnostic
        self._show_timestamp = True
        self._display_mode = "ascii"  # "ascii" / "hex"（终端显示模式）
        self._auto_timer: QTimer | None = None
        self._listen_rx = True  # 是否接收设备主动推送的数据（默认开）
        self._expect_rx_until = 0  # 手动发送后等待响应的截止时间戳（0=不在等待）
        # 接收缓冲区：设备分多次返回的数据拼成一整帧再显示（50ms 静默触发 flush）
        self._rx_buffer: bytearray = bytearray()
        self._rx_flush_timer: QTimer | None = None
        # 日志大小跟踪（估算字节数，超过 10MB 自动保存 txt）
        self._log_size: int = 0
        # 三个 tab 的日志行：[direction, label, hex_content]
        # hex_content 始终存 HEX 字符串，显示时按 _display_mode 转换
        self._lines: dict[str, list[list[str]]] = {"raw": [], "stats": [], "diagnostic": []}
        # 字符格式缓存：(颜色, 是否加粗) → QTextCharFormat
        self._char_formats: dict[tuple[str, bool], QTextCharFormat] = {}
        self._build_ui()
        self._refresh_terminal()
        # 接收串口数据（真实模式）
        serial_manager.data_received.connect(self._on_serial_data)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._build_console())

    def _build_console(self) -> QFrame:
        console = QFrame()
        console.setObjectName("console")
        cl = QVBoxLayout(console)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # ===== console-tabs 行（38px）=====
        tabs_row = QFrame()
        tabs_row.setObjectName("console-tabs")
        tl = QHBoxLayout(tabs_row)
        tl.setContentsMargins(10, 0, 10, 0)
        tl.setSpacing(6)

        self._tab_buttons: dict[str, QPushButton] = {}
        for tab_id, tab_name in [("raw", "串口原始日志"), ("stats", "通信统计"), ("diagnostic", "诊断日志")]:
            btn = QPushButton(tab_name)
            btn.setObjectName("console-tab")
            btn.setProperty("active", "true" if tab_id == "raw" else "false")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, tid=tab_id: self._switch_tab(tid))
            self._tab_buttons[tab_id] = btn
            tl.addWidget(btn)

        tl.addStretch()

        # 自动发送 checkbox + 间隔输入框（放在时间戳前面）
        self.cb_auto = QCheckBox("自动发送")
        self.cb_auto.setObjectName("check-label")
        self.cb_auto.stateChanged.connect(self._on_auto_send_changed)
        tl.addWidget(self.cb_auto, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.input_interval = QLineEdit("1000")
        self.input_interval.setFixedWidth(60)
        self.input_interval.setFixedHeight(24)
        self.input_interval.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl.addWidget(self.input_interval, alignment=Qt.AlignmentFlag.AlignVCenter)
        ms_label = QLabel("ms")
        tl.addWidget(ms_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 时间戳 checkbox
        self.cb_timestamp = QCheckBox("时间戳")
        self.cb_timestamp.setChecked(True)
        self.cb_timestamp.setObjectName("check-label")
        self.cb_timestamp.stateChanged.connect(self._on_timestamp_changed)
        tl.addWidget(self.cb_timestamp)

        # 显示模式按钮：默认 ASCII，点击切换 HEX
        self.btn_display_mode = QPushButton("ASCII")
        self.btn_display_mode.setObjectName("console-tab")
        self.btn_display_mode.setProperty("variant", "secondary")
        self.btn_display_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_display_mode.clicked.connect(self._toggle_display_mode)
        tl.addWidget(self.btn_display_mode)

        # 接收开关：默认"全部显示"，点击切换"仅手动"（设备主动推送的数据是否显示）
        self.btn_listen = QPushButton("全部显示")
        self.btn_listen.setObjectName("console-tab")
        self.btn_listen.setProperty("variant", "secondary")
        self.btn_listen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_listen.clicked.connect(self._toggle_listen)
        tl.addWidget(self.btn_listen)

        # 清空按钮
        btn_clear = QPushButton("清空")
        btn_clear.setObjectName("console-tab")
        btn_clear.setProperty("variant", "secondary")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_current_log)
        tl.addWidget(btn_clear)

        # 立即保存按钮：把当前日志保存为 txt
        btn_save_now = QPushButton("立即保存")
        btn_save_now.setObjectName("console-tab")
        btn_save_now.setProperty("variant", "secondary")
        btn_save_now.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_now.clicked.connect(self._save_now)
        tl.addWidget(btn_save_now)

        # 打开本地保存目录按钮
        btn_open_history = QPushButton("打开本地保存")
        btn_open_history.setObjectName("console-tab")
        btn_open_history.setProperty("variant", "secondary")
        btn_open_history.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_history.clicked.connect(self._open_history_dir)
        tl.addWidget(btn_open_history)

        cl.addWidget(tabs_row)

        # ===== terminal（暗底，弹性）=====
        self.terminal = QPlainTextEdit()
        self.terminal.setObjectName("terminal")
        self.terminal.setReadOnly(True)
        self.terminal.setMaximumBlockCount(TERMINAL_MAX_LINES)  # 限制行数防内存膨胀
        self.terminal.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)  # 不自动换行，长行水平滚动
        cl.addWidget(self.terminal, 1)

        # ===== sendbar（发送栏，底部）=====
        sendbar = QFrame()
        sendbar.setObjectName("sendbar")
        sl = QHBoxLayout(sendbar)
        sl.setContentsMargins(10, 6, 10, 6)
        sl.setSpacing(8)

        # 发送输入框 + 历史按钮
        self.send_input = QLineEdit()
        self.send_input.setPlaceholderText("输入发送内容，如 01 03 00 00 00 01")
        self.send_input.setObjectName("send-input")
        self.send_input.returnPressed.connect(self._send)
        btn_history = QPushButton("历史")
        btn_history.setObjectName("console-tab")
        btn_history.setProperty("variant", "secondary")
        btn_history.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_history.clicked.connect(self._toggle_history)
        sl.addWidget(self.send_input, 1)
        sl.addWidget(btn_history)

        # 发送格式下拉
        sl.addWidget(QLabel("格式"), alignment=Qt.AlignmentFlag.AlignVCenter)
        self.combo_format = QComboBox()
        self.combo_format.addItems(["HEX", "ASCII"])
        self.combo_format.setStyleSheet("QComboBox { min-height: 28px; padding: 0 6px; } QComboBox::drop-down { width: 18px; }")
        sl.addWidget(self.combo_format, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 行结束符下拉（显示 \r \n 符号）
        sl.addWidget(QLabel("行结束符"), alignment=Qt.AlignmentFlag.AlignVCenter)
        self.combo_ending = QComboBox()
        self.combo_ending.addItems(["无", "\\r", "\\n", "\\r\\n"])
        self.combo_ending.setStyleSheet("QComboBox { min-height: 28px; padding: 0 6px; } QComboBox::drop-down { width: 18px; }")
        sl.addWidget(self.combo_ending, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 发送按钮
        self.btn_send = QPushButton("发送")
        self.btn_send.setObjectName("btn-send")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self._send)
        sl.addWidget(self.btn_send)

        cl.addWidget(sendbar)

        # ===== 发送历史浮层 =====
        self.history_panel = QFrame()
        self.history_panel.setObjectName("history-popover")
        self.history_panel.setVisible(False)
        hl = QVBoxLayout(self.history_panel)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        # head
        hist_head = QFrame()
        hist_head.setObjectName("history-head")
        hhl = QHBoxLayout(hist_head)
        hhl.setContentsMargins(10, 0, 10, 0)
        hhl.addWidget(QLabel("最近发送 20 条"))
        hhl.addStretch()
        btn_hist_clear = QPushButton("清空")
        btn_hist_clear.setObjectName("console-tab")
        btn_hist_clear.setProperty("variant", "secondary")
        btn_hist_clear.setFixedSize(56, 24)
        btn_hist_clear.clicked.connect(self._clear_history)
        hhl.addWidget(btn_hist_clear, alignment=Qt.AlignmentFlag.AlignVCenter)
        hl.addWidget(hist_head)
        # list（滚动区）
        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setObjectName("history-scroll")
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(4, 4, 4, 4)
        self.history_layout.setSpacing(2)
        self.history_layout.addStretch()
        self.history_scroll.setWidget(self.history_container)
        hl.addWidget(self.history_scroll, 1)

        # 浮层用绝对定位叠在 sendbar 上方（parent 设为 page 自身，坐标系用 page）
        self.history_panel.setParent(self)
        self.history_panel.raise_()
        self.history_panel.setGeometry(22, self.height() - 250, min(560, self.width() - 44), 200)

        return console

    def resizeEvent(self, event):
        """调整历史浮层位置（浮在 sendbar 上方）"""
        super().resizeEvent(event)
        if hasattr(self, "history_panel"):
            panel_h = 200
            panel_w = min(560, self.width() - 44)
            # 底部留出 sendbar 高度（约 50px）+ page padding（12px）
            x = (self.width() - panel_w) // 2
            y = self.height() - panel_h - 62
            self.history_panel.setGeometry(x, y, panel_w, panel_h)
            self.history_panel.raise_()

    # ===== 日志注入（供协议层调用）=====

    def append_line(self, direction: str, label: str, content: str):
        """向当前 tab 追加一行日志。

        direction: "tx" / "rx" / "info" / "warn"
        label: "TX" / "RX" / "CRC" / "TIMEOUT" / "WARN" 等
        content: HEX 帧 / 日志文本

        分流规则：
        - 串口原始日志(raw)：只显示真实报文 TX/RX 的 HEX 帧
        - 诊断日志(diagnostic)：协议层事件 CRC/TIMEOUT/WARN（带时间戳）
        """
        # 存储时记录时间戳，避免重新渲染时时间漂移
        ts = _now_hms()
        line = [direction, label, content, ts]
        # 协议诊断信息（CRC/TIMEOUT/WARN）只进诊断日志，不污染串口原始日志
        if direction in ("tx", "rx") and label in ("CRC", "TIMEOUT", "WARN"):
            self._lines["diagnostic"].append([direction, label, f"{label}: {content}", ts])
        else:
            # 真实报文（TX/RX HEX 帧）进串口原始日志
            self._lines["raw"].append(line)
            if self._current_tab == "raw":
                self._append_to_terminal(line)
        # 估算日志大小增长，超过阈值自动保存
        self._log_size += len(ts) + len(direction) + len(label) + len(content) + 8
        if self._log_size >= LOG_SIZE_THRESHOLD:
            self._save_log_to_file()

    def _save_log_to_file(self):
        """日志超过 10MB 时，把所有日志保存为 txt 到 history/ 目录，然后清空终端。

        文件名格式：serial_log_YYYY-MM-DD_HHMMSS.txt
        """
        filepath = self._write_log_to_file()
        if filepath:
            # 清空终端和日志数据，重置大小计数
            self._lines = {"raw": [], "stats": [], "diagnostic": []}
            self._log_size = 0
            self._refresh_terminal()

    def _write_log_to_file(self) -> str | None:
        """把当前 raw 日志保存为 txt 到 history/ 目录。返回文件路径，失败返回 None。

        不清空终端（供自动保存和手动保存共用）。
        """
        try:
            os.makedirs(HISTORY_DIR, exist_ok=True)
            filename = f"serial_log_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.txt"
            filepath = os.path.join(HISTORY_DIR, filename)
            lines_text = []
            for line in self._lines["raw"]:
                ts = line[3] if len(line) > 3 else ""
                lines_text.append(f"{ts}  {line[1]}  {line[2]}")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines_text))
            return filepath
        except Exception:
            return None

    def _save_now(self):
        """立即保存：把当前日志保存为 txt（不清空终端）"""
        filepath = self._write_log_to_file()
        if filepath:
            dialogs.success(self, "保存成功", "串口日志已保存到本地。", detail=filepath, reveal=filepath)
        else:
            dialogs.error(self, "日志保存失败", "请确认 history 目录可以写入，然后重试。")

    def _open_history_dir(self):
        """打开本地保存目录（history/）"""
        try:
            os.makedirs(HISTORY_DIR, exist_ok=True)
            import subprocess
            import sys
            if sys.platform == "win32":
                os.startfile(HISTORY_DIR)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", HISTORY_DIR])
            else:
                subprocess.Popen(["xdg-open", HISTORY_DIR])
        except Exception as e:
            dialogs.error(self, "无法打开目录", "请确认 history 目录存在。", detail=str(e))

    def _line_segments(self, line: list[str]) -> Segments:
        """一行日志在终端里的显示定义。

        终端显示格式的唯一定义处：实时追加和整体重绘共用，两条路径显示一致。
        content 始终存 HEX 字符串，显示时按 _display_mode 转换：
        - hex: 原样显示 HEX
        - ascii: HEX → ASCII 文本（不可打印字符显示为 .）
        时间戳用行存储时的值（line[3]），避免重新渲染时时间漂移。
        """
        direction, label, content = line[0], line[1], line[2]
        stored_ts = line[3] if len(line) > 3 else ""
        # 报文行（TX/RX）正文直接用方向色（RX 绿 / TX 蓝），行首不再显示标签：
        # 颜色已经区分收发方向，标签是重复信息。
        # 诊断行（TIMEOUT/CRC/WARN）和 INFO 提示的正文保持深色——
        # 它们同样带 tx/rx 方向，按方向上色会把"超时"显示成绿色
        is_frame = direction in ("tx", "rx") and label in ("TX", "RX")
        # 只有报文行的内容才是 HEX 帧，才按显示模式转换。
        # 诊断行虽然也带 tx/rx 方向，内容却是文字，按 HEX 转换会变成一串点
        if is_frame and self._display_mode == "ascii":
            display_content = _hex_to_ascii(content)
        else:
            display_content = content
        # 方向色（白底用深色，保证可读）
        color_map = {
            "tx": "#0b6fb3",   # 深蓝（TX）
            "rx": "#11875d",   # 深绿（RX）
            "warn": "#bf3a46", # 红（WARN）
            "info": "#617083", # 灰（INFO）
        }
        color = color_map.get(direction, TEXT_COLOR)
        content_color = color if is_frame or direction == "warn" else TEXT_COLOR
        segments: Segments = []
        if self._show_timestamp and stored_ts:
            segments += [(stored_ts, TIMESTAMP_COLOR, True), ("  ", TEXT_COLOR, False)]
        # 行首标签只给非报文行（TIMEOUT/WARN/INFO 等）；报文行靠颜色区分方向
        if not is_frame:
            segments += [(label, color, True), ("  ", TEXT_COLOR, False)]
        segments.append((display_content, content_color, False))
        return segments

    def _stats_segments(self, line: list[str]) -> Segments:
        """统计 tab 行格式（白底深色，和原始日志一致）"""
        direction, label, content = line[0], line[1], line[2]
        color = "#11875d" if direction == "rx" else "#0b6fb3"
        return [(label, color, True), ("  ", TEXT_COLOR, False), (content, TEXT_COLOR, False)]

    def _char_format(self, color: str, bold: bool) -> QTextCharFormat:
        """取（并缓存）指定颜色/粗细的字符格式"""
        key = (color, bold)
        fmt = self._char_formats.get(key)
        if fmt is None:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            self._char_formats[key] = fmt
        return fmt

    def _render_lines(self, lines: list[list[str]], segments_of: Callable[[list[str]], Segments]) -> None:
        """把若干行日志写到终端末尾。

        直接用 QTextCursor 写带格式的文本，不拼 HTML：一是不必逐行解析 HTML，
        二是内容里的 < > & 等字符会原样显示，不会被当成标签吃掉。
        所有行放在同一个编辑块里：写完之前不触发布局和滚动条重算，
        所以整体重绘几千行也只付出一次布局的代价。
        """
        doc = self.terminal.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.End)
        # 文档为空（刚清空）时首行直接写进现有的空块，避免顶部多出一个空行
        need_block = not doc.isEmpty()
        cursor.beginEditBlock()
        for line in lines:
            segments = segments_of(line)
            if need_block:
                cursor.insertBlock()
            for text, color, bold in segments:
                if text:
                    cursor.insertText(text, self._char_format(color, bold))
            need_block = True
        cursor.endEditBlock()

    def _scroll_to_bottom(self):
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _append_to_terminal(self, line: list[str]):
        """追加一行到终端，并滚动到底部"""
        self._render_lines([line], self._line_segments)
        self._scroll_to_bottom()

    def _refresh_terminal(self):
        """重建终端内容（切换 tab / 时间戳变化时）"""
        cap = self.terminal.document().maximumBlockCount()
        # 终端最多只留 cap 行，更早的行渲染出来也会立刻被丢弃，所以只重绘最后 cap 行
        lines = self._lines.get(self._current_tab, [])[-cap:]
        self.terminal.clear()
        if self._current_tab == "stats":
            self._render_lines(lines, self._stats_segments)
        else:
            self._render_lines(lines, self._line_segments)
        self._scroll_to_bottom()

    # ===== tab 切换 =====

    def _switch_tab(self, tab_id: str):
        self._current_tab = tab_id
        for tid, btn in self._tab_buttons.items():
            btn.setProperty("active", "true" if tid == tab_id else "false")
            btn.style().polish(btn)
        if tab_id == "stats":
            self._refresh_stats()
        else:
            self._refresh_terminal()

    def _on_timestamp_changed(self):
        self._show_timestamp = self.cb_timestamp.isChecked()
        self._refresh_terminal()

    def _toggle_display_mode(self):
        """切换终端显示模式：ASCII ↔ HEX"""
        self._display_mode = "hex" if self._display_mode == "ascii" else "ascii"
        self.btn_display_mode.setText("HEX" if self._display_mode == "hex" else "ASCII")
        self._refresh_terminal()

    def _toggle_listen(self):
        """切换接收开关：是否显示设备主动推送的数据"""
        self._listen_rx = not self._listen_rx
        self.btn_listen.setText("全部显示" if self._listen_rx else "仅手动")

    # ===== 发送 =====

    def _send(self):
        raw = self.send_input.text().strip()
        if not raw:
            return
        if not serial_manager.is_connected:
            self.append_line("warn", "WARN", "串口未连接，无法发送")
            return

        fmt = self.combo_format.currentText()
        ending = self.combo_ending.currentText()

        # 解析为字节
        if fmt == "HEX":
            bytes_list = _parse_hex(raw)
            if bytes_list is None:
                self.append_line("warn", "WARN", "HEX 格式非法，请输入如 01 03 00 00")
                return
        else:
            bytes_list = _ascii_to_bytes(raw)

        # 追加行结束符
        ending_bytes = list(LINE_ENDINGS.get(ending, b""))
        bytes_list = bytes_list + ending_bytes
        data = bytes(bytes_list)

        # 发送
        serial_manager.send(data)

        # 终端追加 TX 行
        hex_str = _bytes_to_hex(data)
        self.append_line("tx", "TX", hex_str)

        # 模拟模式下，串口管理器会在 transact 里生成回包
        # 手动发送也生成模拟回包（仅模拟模式）
        if serial_manager.is_mock:
            resp = serial_manager._mock_response(data)
            if resp:
                self.append_line("rx", "RX", _bytes_to_hex(resp))
        else:
            # 真实设备模式：开启 1 秒响应等待窗口
            # 窗口内收到的 RX 始终显示，不受"接收"开关控制
            self._expect_rx_until = time.time() + 1.0

        # 写入发送历史（记录内容 + 格式 + 行结束符）
        store.push_send_history(raw, fmt, ending)
        # 历史面板打开时实时刷新
        if self.history_panel.isVisible():
            self._render_history()

    # ===== 自动发送 =====

    def _on_auto_send(self, state: int):
        if state == Qt.CheckState.Checked.value:
            self._start_auto_send()
        else:
            self._stop_auto_send()

    def _on_auto_send_changed(self):
        if self.cb_auto.isChecked():
            self._start_auto_send()
        else:
            self._stop_auto_send()

    def _start_auto_send(self):
        if not serial_manager.is_connected:
            self.cb_auto.setChecked(False)
            self.append_line("warn", "WARN", "串口未连接，无法自动发送")
            return
        self._stop_auto_send()
        try:
            interval = max(100, int(self.input_interval.text()))
        except ValueError:
            interval = 1000
        self._auto_timer = QTimer()
        self._auto_timer.timeout.connect(self._send)
        self._auto_timer.start(interval)
        self.append_line("info", "INFO", f"自动发送已启动，间隔 {interval} ms")

    def _stop_auto_send(self):
        if self._auto_timer:
            self._auto_timer.stop()
            self._auto_timer = None
            self.append_line("info", "INFO", "自动发送已停止")

    # ===== 清空 =====

    def _clear_current_log(self):
        count = len(self._lines.get(self._current_tab, []))
        self._lines[self._current_tab] = []
        # 清空 raw 时重置大小计数
        if self._current_tab == "raw":
            self._log_size = 0
        self._refresh_terminal()

    # ===== 发送历史 =====

    def _toggle_history(self):
        self.history_panel.setVisible(not self.history_panel.isVisible())
        if self.history_panel.isVisible():
            self._render_history()

    def _render_history(self):
        # 清空旧项（保留 stretch）
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not store.send_history:
            empty = QLabel("暂无发送历史")
            empty.setStyleSheet(f"color: {theme.HEX['MUTED']}; padding: 12px;")
            self.history_layout.insertWidget(0, empty)
            return
        for entry in store.send_history[:20]:
            # 兼容旧格式（纯字符串）和新格式（dict）
            if isinstance(entry, dict):
                text = entry.get("text", "")
                fmt = entry.get("fmt", "HEX")
                ending = entry.get("ending", "无")
            else:
                text = entry
                fmt = "HEX"
                ending = "无"
            item = QFrame()
            item.setObjectName("history-item")
            il = QHBoxLayout(item)
            il.setContentsMargins(8, 0, 8, 0)
            il.setSpacing(8)
            # 显示内容 + 格式 + 行结束符标签
            label_text = f"{text}  [{fmt} / {ending}]"
            pick = QPushButton(label_text)
            pick.setObjectName("history-pick")
            pick.setCursor(Qt.CursorShape.PointingHandCursor)
            pick.clicked.connect(lambda checked=False, e=entry: self._pick_history(e))
            btn_del = QPushButton("X")
            btn_del.setObjectName("history-delete")
            btn_del.setFixedSize(28, 28)
            btn_del.setStyleSheet("QPushButton { padding: 0; min-height: 0; }")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.clicked.connect(lambda checked=False, e=entry: self._delete_history(e))
            il.addWidget(pick, 1)
            il.addWidget(btn_del)
            self.history_layout.insertWidget(self.history_layout.count() - 1, item)

    def _pick_history(self, entry):
        """选择历史项：恢复内容 + 格式 + 行结束符"""
        if isinstance(entry, dict):
            text = entry.get("text", "")
            fmt = entry.get("fmt", "HEX")
            ending = entry.get("ending", "无")
        else:
            text = entry
            fmt = "HEX"
            ending = "无"
        self.send_input.setText(text)
        self.combo_format.setCurrentText(fmt)
        self.combo_ending.setCurrentText(ending)
        self.send_input.setFocus()
        self.history_panel.setVisible(False)

    def _delete_history(self, entry):
        """删除单条历史（按 text 匹配）"""
        text = entry.get("text") if isinstance(entry, dict) else entry
        store.send_history = [h for h in store.send_history
                              if (h.get("text") if isinstance(h, dict) else h) != text]
        store._save_history()
        self._render_history()

    def _clear_history(self):
        store.send_history = []
        store._save_history()
        self._render_history()

    # ===== 串口数据接收（真实模式）=====

    def _on_serial_data(self, data: bytes):
        """真实模式下串口读线程收到的数据。

        设备可能分多次返回一个完整响应，用缓冲区拼接：
        每次收到数据追加到缓冲区，重置 50ms 定时器，
        定时器触发时（50ms 内无新数据）把缓冲区拼成一整帧显示为一行 RX。
        """
        now = time.time()
        # 不在接收范围（开关关且不在响应窗口）→ 丢弃
        if not self._listen_rx and now >= self._expect_rx_until:
            return
        # 追加到缓冲区
        self._rx_buffer.extend(data)
        # 重置 flush 定时器（50ms 静默后触发）
        if self._rx_flush_timer is None:
            self._rx_flush_timer = QTimer()
            self._rx_flush_timer.setSingleShot(True)
            self._rx_flush_timer.timeout.connect(self._flush_rx_buffer)
        self._rx_flush_timer.start(50)

    def _flush_rx_buffer(self):
        """缓冲区 flush：把累积的接收数据作为一行 RX 显示"""
        if not self._rx_buffer:
            return
        hex_str = _bytes_to_hex(bytes(self._rx_buffer))
        self._rx_buffer.clear()
        self.append_line("rx", "RX", hex_str)

    # ===== 统计 tab =====

    def _refresh_stats(self):
        """刷新统计 tab 内容。

        统计按连接会话计：新建连接清零，连接期间丢包率单调累计不回退。
        """
        self._lines["stats"] = []
        stats = serial_manager.get_stats()
        # 丢包率：本次连接失败次数 / 请求次数（timeout + crc_error 计入失败）
        tx_frames = stats["tx_frames"]
        failures = stats["tx_failures"]
        loss_rate = f"{failures / tx_frames * 100:.1f}%" if tx_frames > 0 else "0%"
        rows = [
            ["tx", "TX", f'{stats["tx_bytes"]:,} B / {tx_frames} 帧'],
            ["rx", "RX", f'{stats["rx_bytes"]:,} B / {stats["rx_frames"]} 帧'],
            ["tx", "丢包", f'{failures} 次 / {loss_rate}（本次连接 失败/总请求）'],
            ["rx", "CRC", f'{stats["crc_errors"]} 次（本次连接）'],
        ]
        self._lines["stats"] = rows
        self._refresh_terminal()

    # ===== 生命周期 =====

    def hideEvent(self, event):
        """离开页面时停止自动发送"""
        super().hideEvent(event)
        self._stop_auto_send()


class _ProtocolLogBridge(QObject):
    """协议日志跨线程桥。

    协议层在 PollWorker 后台线程调用 protocol_log_callback，不能直接
    append 到主线程的 QPlainTextEdit（QTextDocument 非线程安全，
    跨线程 appendHtml 会创建错线程的 QObject 子项 → 堆损坏）。
    经 Signal emit 后由 Qt 按接收者所在线程排队投递到主线程执行。
    """
    line = Signal(str, str, str)


# 模块级单例（主线程创建，信号亲和主线程）
_protocol_log_bridge = _ProtocolLogBridge()


def protocol_log_callback(direction: str, label: str, content: str):
    """全局日志回调函数，供协议层注入 TX/RX 行到串口终端。

    PollWorker 在后台线程创建 ModbusProtocol 时，用此函数作为 log_callback。
    受"全部显示/仅手动"开关控制：仅手动模式下不显示自动轮询的报文。
    注意：本函数可能在 worker 线程被调用，只做信号投递，不直接碰任何控件。
    """
    if SerialPage._instance:
        # 协议层自动轮询的 TX/RX 受 _listen_rx 开关控制
        # （手动发送走 SerialPage._send → append_line，不受此开关控制）
        if not SerialPage._instance._listen_rx:
            return
        _protocol_log_bridge.line.emit(direction, label, content)
