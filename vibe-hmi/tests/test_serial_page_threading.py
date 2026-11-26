"""
串口页跨线程日志投递测试

回归背景：协议层在 PollWorker 后台线程直接调用 protocol_log_callback →
append_line → 直接写终端文档，跨线程操作 QTextDocument（非线程安全），
Qt 报 "Cannot create children for a parent that is in a different thread"，
长时间运行后随机堆损坏导致应用卡死/崩溃（打包版运行约半小时复现）。

修复后：回调只 emit 信号，由 Qt 排队投递到主线程执行 append_line。

探针：监听终端文档的 contentsChange 信号，记录每次"文档被修改"时所在的线程。
它直接对应被破坏的不变量——终端文档只能在主线程被修改——不依赖具体怎么写。

运行：
    cd vibe-hmi
    .venv/Scripts/python.exe -m pytest tests/test_serial_page_threading.py -v
"""
import os
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _watch_doc_changes(page) -> list[int]:
    """返回一个列表，终端文档每次被修改就追加当时的线程 id"""
    seen: list[int] = []
    page.terminal.document().contentsChange.connect(lambda *args: seen.append(threading.get_ident()))
    return seen


def _call_from_worker(callback) -> None:
    t = threading.Thread(target=callback)
    t.start()
    t.join()


class TestProtocolLogThreadSafety:
    def test_callback_defers_to_main_thread(self, qapp):
        """worker 线程调用回调：不直接改文档，投递到主线程后才写终端。"""
        from src.pages.serial_page import SerialPage, protocol_log_callback

        page = SerialPage()
        main_ident = threading.get_ident()
        seen = _watch_doc_changes(page)

        _call_from_worker(lambda: protocol_log_callback("tx", "TX", "01 03 00 00 00 01 84 0A"))

        # 1) 回调返回时不得直接改文档（跨线程写是被修复的 bug）
        assert seen == [], "回调在工作线程内直接修改了终端文档"

        # 2) 主线程事件循环处理后，文档必须只被主线程修改过
        qapp.processEvents()
        assert seen, "日志行没有写入终端"
        assert set(seen) == {main_ident}, f"终端文档在非主线程被修改：{seen}"

    def test_listen_rx_off_drops_lines(self, qapp):
        """仅手动模式（_listen_rx=False）：协议日志不投递。"""
        from src.pages.serial_page import SerialPage, protocol_log_callback

        page = SerialPage()
        page._listen_rx = False
        seen = _watch_doc_changes(page)

        _call_from_worker(lambda: protocol_log_callback("rx", "RX", "01 03"))
        qapp.processEvents()

        assert seen == []
