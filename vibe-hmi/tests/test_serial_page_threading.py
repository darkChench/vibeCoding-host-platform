"""
串口页跨线程日志投递测试

回归背景：协议层在 PollWorker 后台线程直接调用 protocol_log_callback →
append_line → terminal.appendHtml，跨线程操作 QTextDocument（非线程安全），
Qt 报 "Cannot create children for a parent that is in a different thread"，
长时间运行后随机堆损坏导致应用卡死/崩溃（打包版运行约半小时复现）。

修复后：回调只 emit 信号，由 Qt 排队投递到主线程执行 append_line。

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


class TestProtocolLogThreadSafety:
    def test_callback_defers_to_main_thread(self, qapp):
        """worker 线程调用回调：不直接碰控件，投递到主线程后才 append。"""
        from src.pages.serial_page import SerialPage, protocol_log_callback

        page = SerialPage()
        main_ident = threading.get_ident()
        appends: list[int] = []

        # 探针：记录 appendHtml 实际执行线程（遮蔽实例属性，Python 层查找生效）
        page.terminal.appendHtml = lambda html: appends.append(threading.get_ident())

        t = threading.Thread(
            target=lambda: protocol_log_callback("tx", "TX", "01 03 00 00 00 01 84 0A")
        )
        t.start()
        t.join()

        # 1) 回调返回时不得直接操作控件（跨线程 append 是被修复的 bug）
        assert appends == [], "回调在工作线程内直接操作了终端控件"

        # 2) 主线程事件循环处理后，append 必须发生在主线程
        qapp.processEvents()
        assert appends == [main_ident], "日志行未投递到主线程执行"

    def test_listen_rx_off_drops_lines(self, qapp):
        """仅手动模式（_listen_rx=False）：协议日志不投递。"""
        from src.pages.serial_page import SerialPage, protocol_log_callback

        page = SerialPage()
        page._listen_rx = False
        appends: list[int] = []
        page.terminal.appendHtml = lambda html: appends.append(threading.get_ident())

        t = threading.Thread(target=lambda: protocol_log_callback("rx", "RX", "01 03"))
        t.start()
        t.join()
        qapp.processEvents()

        assert appends == []
