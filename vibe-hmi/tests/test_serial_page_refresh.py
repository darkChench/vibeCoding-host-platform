"""
串口页终端整体重绘测试

回归背景：切换页签、勾选时间戳、切换 HEX/ASCII 会触发终端整体重绘。原实现把存储的
全部日志行逐行 appendHtml 重画一遍——终端最多只保留有限的行数，而存储的列表可以到
两万多行，日志积累后一次操作就冻结界面十秒左右；清空后恢复。

修复后的约定：
- 整体重绘只渲染终端留得住的最后几行（不超过行数上限）
- 多行写入放在同一个编辑块里，文档只在最后变更一次，而不是每行一次

运行：
    cd vibe-hmi
    .venv/Scripts/python.exe -m pytest tests/test_serial_page_refresh.py -v
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

FRAME = "01 03 10 00 64 00 C8 00 FA 01 2C 00 00 00 00 41 B8"
CAP = 200


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _filled_page(stored: int):
    """返回一个存储了 stored 行日志的串口页（行数上限降到 CAP，便于快速到顶）。"""
    from src.pages.serial_page import SerialPage

    page = SerialPage()
    page._display_mode = "hex"
    page.terminal.document().setMaximumBlockCount(CAP)
    for i in range(stored):
        page.append_line("rx", "RX", f"{i:04X} {FRAME}")
    return page


def _doc_change_count(action) -> int:
    """执行 action，返回期间终端文档 contentsChange 信号的次数。"""
    page = _filled_page(CAP * 4)
    changes = []
    page.terminal.document().contentsChange.connect(lambda *args: changes.append(args))
    action(page)
    return len(changes)


class TestRefreshBounded:
    def test_refresh_changes_document_once(self, qapp):
        """整体重绘 = 清空 + 恰好一次批量写入，不能是每行改一次文档。

        Qt 的 clear() 自身会发出几次 contentsChange，所以用"只清空"作为基线来比。
        """
        clear_only = _doc_change_count(lambda page: page.terminal.clear())
        refresh = _doc_change_count(lambda page: page._switch_tab("raw"))
        assert refresh == clear_only + 1, (
            f"整体重绘改了 {refresh} 次文档（只清空是 {clear_only} 次），"
            f"应为清空之后只写入 1 次"
        )

    def test_refresh_renders_only_lines_terminal_keeps(self, qapp, monkeypatch):
        """整体重绘：只处理终端留得住的最后 CAP 行，更早的行渲染出来也会被丢弃。"""
        from src.pages.serial_page import SerialPage

        page = _filled_page(CAP * 4)
        rendered = []
        original = SerialPage._line_segments
        monkeypatch.setattr(
            SerialPage, "_line_segments",
            lambda self, line: rendered.append(line) or original(self, line),
        )
        page._switch_tab("raw")
        assert len(rendered) == CAP

    def test_refresh_shows_newest_lines(self, qapp):
        """整体重绘后：终端是满的，且显示的是最新 CAP 行。"""
        page = _filled_page(CAP * 4)
        page._switch_tab("raw")
        doc = page.terminal.document()
        assert doc.blockCount() == CAP
        assert f"{CAP * 4 - CAP:04X} {FRAME}" in doc.firstBlock().text()
        assert f"{CAP * 4 - 1:04X} {FRAME}" in doc.lastBlock().text()

    def test_clear_keeps_working(self, qapp):
        """清空后重绘不残留任何行。"""
        page = _filled_page(CAP * 4)
        page._clear_current_log()
        page._switch_tab("raw")
        assert page.terminal.document().blockCount() == 1
        assert page.terminal.document().firstBlock().text() == ""
