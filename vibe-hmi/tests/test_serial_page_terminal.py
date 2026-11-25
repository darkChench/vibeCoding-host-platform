"""
串口页终端渲染测试

验证原始日志的报文行按方向自动着色且不显示行首标签：RX 绿、TX 蓝，颜色即方向。
诊断行（TIMEOUT/CRC/WARN）和 INFO 提示行不在改动范围内：正文保持深色、标签保留——
它们同样带 tx/rx 方向，若按方向给正文上色，"超时"会被显示成绿色。

运行：
    cd vibe-hmi
    .venv/Scripts/python.exe -m pytest tests/test_serial_page_terminal.py -v
"""
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

FRAME = "01 03 00 00"


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _content_color(html: str) -> str:
    """取出报文正文那层 span 的颜色（正文 span 只带 color，没有 font-weight）。"""
    pattern = r'<span style="color:(#[0-9a-fA-F]{6});">[^<]*' + re.escape(FRAME) + "</span>"
    m = re.search(pattern, html)
    assert m, f"未找到报文正文的 span：{html}"
    return m.group(1)


def _label_text(html: str) -> str | None:
    """取出行首标签（粗体 span）的文本；该行没有标签时返回 None。"""
    m = re.search(r'<span style="[^"]*font-weight:bold;">([^<]*)</span>', html)
    return m.group(1) if m else None


class TestDirectionColor:
    @pytest.mark.parametrize(
        "tab,direction,label,body_color,label_shown",
        [
            ("raw", "rx", "RX", "#11875d", False),             # RX 报文：绿，无标签
            ("raw", "tx", "TX", "#0b6fb3", False),             # TX 报文：蓝，无标签
            ("diagnostic", "rx", "TIMEOUT", "#17202c", True),  # 诊断行：正文深色，标签保留
            ("raw", "info", "INFO", "#17202c", True),          # 提示行：正文深色，标签保留
        ],
    )
    def test_frame_lines_are_colored_without_label(
        self, qapp, tab: str, direction: str, label: str, body_color: str, label_shown: bool
    ):
        from src.pages.serial_page import SerialPage

        page = SerialPage()
        page._display_mode = "hex"    # 正文保持 HEX 原文，便于定位
        page._show_timestamp = False  # 关掉时间戳，行首的粗体 span 就只可能是标签
        page.append_line(direction, label, FRAME)
        page._current_tab = tab
        captured: list[str] = []
        page.terminal.appendHtml = captured.append
        page._refresh_terminal()

        assert len(captured) == 1
        assert _content_color(captured[0]) == body_color
        assert _label_text(captured[0]) == (label if label_shown else None)
