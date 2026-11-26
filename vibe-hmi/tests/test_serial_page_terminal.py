"""
串口页终端渲染测试

验证终端里实际渲染出来的文字和颜色：
- 报文行按方向着色且不显示行首标签：RX 绿、TX 蓝，颜色即方向
- 诊断行（TIMEOUT/CRC/WARN）和 INFO 提示行不在着色范围内：正文保持深色、标签保留——
  它们同样带 tx/rx 方向，若按方向给正文上色，"超时"会被显示成绿色
- ASCII 显示模式原样显示设备输出：< > & 不被当成标记吃掉，连续空格不被压缩，
  \\r\\n 是同一个文本块内的换行（原来靠 HTML 渲染，这三点都不成立）

运行：
    cd vibe-hmi
    .venv/Scripts/python.exe -m pytest tests/test_serial_page_terminal.py -v
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

FRAME = "01 03 00 00"
TEXT_COLOR = "#17202c"


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _fragments(page, block_number: int = -1) -> list[tuple[str, str, bool]]:
    """取某个文本块的全部片段：[(文本, 颜色, 是否加粗), ...]（默认取最后一行）"""
    doc = page.terminal.document()
    block = doc.lastBlock() if block_number < 0 else doc.findBlockByNumber(block_number)
    out, it = [], block.begin()
    while not it.atEnd():
        frag = it.fragment()
        fmt = frag.charFormat()
        out.append((frag.text(), fmt.foreground().color().name(), fmt.fontWeight() >= 700))
        it += 1
    return out


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
        page._show_timestamp = False  # 关掉时间戳，行首的粗体片段就只可能是标签
        page.append_line(direction, label, FRAME)
        page._current_tab = tab
        page._refresh_terminal()

        frags = _fragments(page)
        # 正文片段：不加粗、且包含报文内容的那一个（诊断行正文是 "TIMEOUT: ..."）
        body = [f for f in frags if not f[2] and FRAME in f[0]]
        assert len(body) == 1, f"正文片段应为 1 个：{frags}"
        assert body[0][1:] == (body_color, False), body[0]
        labels = [f[0] for f in frags if f[2]]
        assert labels == ([label] if label_shown else []), frags

    def test_line_text_layout(self, qapp):
        """时间戳开/关时的整行文字。"""
        from src.pages.serial_page import SerialPage

        page = SerialPage()
        page._display_mode = "hex"
        page.append_line("rx", "RX", FRAME)
        ts = page._lines["raw"][-1][3]
        page._refresh_terminal()
        assert page.terminal.document().lastBlock().text() == f"{ts}  {FRAME}"

        page._show_timestamp = False
        page._refresh_terminal()
        assert page.terminal.document().lastBlock().text() == FRAME

        page.append_line("info", "INFO", "自动发送已停止")
        assert page.terminal.document().lastBlock().text() == "INFO  自动发送已停止"


class TestAsciiDisplayIsLiteral:
    """ASCII 模式：终端显示的就是设备输出的原文。"""

    @pytest.mark.parametrize(
        "payload,expected",
        [
            (b"<b>ok</b> & <err> v1.2\r\n", "<b>ok</b> & <err> v1.2\u2028"),
            (b"a  b   c\r\n", "a  b   c\u2028"),
            (b"AT+VER?\r\n\r\nOK\r\n", "AT+VER?\u2028\u2028OK\u2028"),
        ],
    )
    def test_device_text_shown_as_is(self, qapp, payload: bytes, expected: str):
        from src.pages.serial_page import SerialPage, _bytes_to_hex

        page = SerialPage()
        page._display_mode = "ascii"
        page._show_timestamp = False
        page.append_line("rx", "RX", _bytes_to_hex(payload))

        doc = page.terminal.document()
        assert doc.blockCount() == 1, "一条日志应占一个文本块（换行在块内）"
        assert doc.lastBlock().text() == expected
        assert _fragments(page)[-1][1] == "#11875d", "RX 报文正文应为绿色"

    def test_diagnostic_text_not_decoded_as_hex(self, qapp):
        """诊断行的内容是文字，不是 HEX 帧：ASCII 模式下也必须原样显示。

        回归：诊断行带 rx/tx 方向，曾被当成 HEX 帧转换，整行显示成 "TIMEOUT  ........."。
        """
        from src.pages.serial_page import SerialPage

        page = SerialPage()
        page._display_mode = "ascii"
        page._show_timestamp = False
        page.append_line("rx", "TIMEOUT", "等待 1000ms 无响应")
        page._switch_tab("diagnostic")
        assert page.terminal.document().lastBlock().text() == "TIMEOUT  TIMEOUT: 等待 1000ms 无响应"


class TestHexToAscii:
    """HEX 帧 → ASCII 显示文本的映射规则"""

    @pytest.mark.parametrize(
        "payload,expected",
        [
            (b"OK\r\n", "OK\u2028"),                   # \r\n 算一个换行
            (b"a\rb\nc", "a\u2028b\u2028c"),           # 单独的 \r、\n 各算一个
            (b"a\r\r\n\nb", "a\u2028\u2028\u2028b"),   # 相邻的 \r 和 \r\n、\n
            (b"\x00\x1f\x7f\x80\xff", "....."),       # 不可打印字节显示为 .
            (b"<b> & </b>  x", "<b> & </b>  x"),      # 可打印字符原样，空格不压缩
            (b"", ""),
        ],
    )
    def test_mapping(self, payload: bytes, expected: str):
        from src.pages.serial_page import _hex_to_ascii, _bytes_to_hex

        assert _hex_to_ascii(_bytes_to_hex(payload)) == expected

    def test_same_as_byte_by_byte_reference(self):
        """与原先逐字节实现在随机帧上的结果一致（整帧转换是为了提速，规则不能变）。"""
        import random

        from src.pages.serial_page import _hex_to_ascii, _bytes_to_hex, ASCII_LINE_BREAK

        def reference(hex_str: str) -> str:
            cleaned, chars, i = hex_str.replace(" ", ""), [], 0
            while i < len(cleaned) - 1:
                try:
                    b = int(cleaned[i:i + 2], 16)
                    if b == 0x0D and i + 2 < len(cleaned) and int(cleaned[i + 2:i + 4], 16) == 0x0A:
                        chars.append(ASCII_LINE_BREAK)
                        i += 4
                        continue
                    chars.append(ASCII_LINE_BREAK if b in (0x0D, 0x0A)
                                 else chr(b) if 32 <= b < 127 else ".")
                except ValueError:
                    chars.append(".")
                i += 2
            return "".join(chars)

        rng = random.Random(20261126)
        alphabet = [0x0D, 0x0A, 0x00, 0x1F, 0x20, 0x7E, 0x7F, 0x80, 0xFF] + list(range(0x21, 0x7F))
        for _ in range(500):
            data = bytes(rng.choice(alphabet) for _ in range(rng.randrange(0, 80)))
            hex_str = _bytes_to_hex(data)
            assert _hex_to_ascii(hex_str) == reference(hex_str), data
