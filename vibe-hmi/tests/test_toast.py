"""
轻提示测试

验证 toast 模块的行为约定：
- 出现在窗口右下角，随窗口大小重新摆放；多条堆叠，最新的在最下面
- 到时间自动消失；鼠标停在上面时不消失
- 带操作按钮时，点击执行回调并消失

运行：
    cd vibe-hmi
    .venv/Scripts/python.exe -m pytest tests/test_toast.py -v
"""
import gc
import os
import weakref

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from shiboken6 import delete, isValid
from PySide6.QtCore import QEvent, QPointF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from src import toast


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def host(qapp):
    window = QWidget()
    window.resize(900, 600)
    window.show()
    qapp.processEvents()
    yield window
    for item in list(toast._active):
        if isValid(item):
            item._remove()
    QApplication.processEvents()
    if isValid(window):
        window.close()


def _right_edge(item) -> int:
    """提示条（不含阴影余量）的右边缘位置"""
    return item.x() + item.width() - toast._PAD


def _bottom_edge(item) -> int:
    return item.y() + item.height() - toast._PAD


class TestToast:
    def test_appears_at_bottom_right(self, host):
        item = toast.show(host, "已删除 3 条报警记录")
        assert item.isVisible()
        assert _right_edge(item) == host.width() - toast._MARGIN_RIGHT
        assert _bottom_edge(item) == host.height() - toast._MARGIN_BOTTOM

    def test_follows_window_resize(self, host):
        item = toast.show(host, "已保存")
        host.resize(1200, 720)
        qapp = QApplication.instance()
        qapp.processEvents()
        assert _right_edge(item) == 1200 - toast._MARGIN_RIGHT
        assert _bottom_edge(item) == 720 - toast._MARGIN_BOTTOM

    def test_stacks_with_newest_at_bottom(self, host):
        first = toast.show(host, "第一条")
        second = toast.show(host, "第二条")
        assert _right_edge(first) == _right_edge(second)
        assert _bottom_edge(first) == second.y() + toast._PAD - toast._GAP, "先出现的应被顶到上面，间隔 10"

    def test_auto_dismisses(self, host):
        item = toast.show(host, "自动消失", duration_ms=60)
        QTest.qWait(60 + toast._FADE_OUT_MS + 150)
        assert item not in toast._active

    def test_stays_while_hovered(self, host):
        item = toast.show(host, "别走", duration_ms=60)
        enter = QEvent(QEvent.Type.Enter)
        QApplication.sendEvent(item, enter)
        QTest.qWait(250)
        assert item in toast._active, "鼠标停在提示上时不应消失"
        QApplication.sendEvent(item, QEvent(QEvent.Type.Leave))
        QTest.qWait(60 + toast._FADE_OUT_MS + 150)
        assert item not in toast._active

    def test_action_button_runs_callback_and_dismisses(self, host):
        calls = []
        item = toast.show(host, "参数地址重复，未能保存", kind=toast.WARNING,
                          action_text="查看", on_action=lambda: calls.append(1))
        item._action_btn.click()
        assert calls == [1]
        QTest.qWait(toast._FADE_OUT_MS + 150)
        assert item not in toast._active

    def test_empty_text_shows_nothing(self, host):
        assert toast.show(host, "") is None
        assert toast._active == []

    def test_stale_toasts_are_dropped_when_host_destroyed(self, host):
        """宿主窗口被销毁时它上面的轻提示跟着销毁：之后的轻提示照常显示，不会碰到失效对象。"""
        toast.show(host, "窗口马上没了", duration_ms=60000)
        other = QWidget()
        other.resize(500, 400)
        other.show()
        delete(host)  # 立即销毁（deleteLater 的事件在顶层 processEvents 里不会被处理）
        QApplication.processEvents()
        item = toast.show(other, "新窗口上的提示", duration_ms=60000)
        QApplication.processEvents()
        assert toast._active == [item]
        assert _right_edge(item) == other.width() - toast._MARGIN_RIGHT
        item._remove()
        QApplication.processEvents()
        other.close()

    def test_destroyed_after_dismiss_even_if_wrappers_collected(self, host):
        """回归：消失后的销毁不能依赖延迟删除（原因见 tests/test_dialogs.py 的同类测试）。"""
        item = toast.show(host, "自动消失", duration_ms=60)
        alive = weakref.ref(item)
        del item
        gc.collect()
        QTest.qWait(60 + toast._FADE_OUT_MS + 150)  # 等待：到时 → 淡出 → 下一轮事件循环销毁
        gc.collect()
        assert alive() is None, "消失之后轻提示的 Python 对象应被释放"
