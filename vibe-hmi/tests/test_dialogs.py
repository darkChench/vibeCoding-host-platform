"""
应用内弹框测试

验证 dialogs 模块的行为约定：
- 通知类（成功 / 信息 / 警告 / 错误）不阻塞；主按钮、Enter、Esc、点遮罩、右上角 × 都能关闭
- 确认类阻塞并返回是否确认；危险或不可恢复的确认：默认焦点在"取消"、没有关闭按钮、点遮罩不关闭
- 焦点只在卡片内部循环；文字一律按纯文本显示；详情区高度贴合内容
- 同一时间只显示一个弹框，其余排队；遮罩跟随窗口大小

运行：
    cd vibe-hmi
    .venv/Scripts/python.exe -m pytest tests/test_dialogs.py -v
"""
import gc
import os
import weakref

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from shiboken6 import delete, isValid
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QKeyEvent, QTextDocument
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QWidget

from src import dialogs

LONG_REPORT = "\n".join(f"  第 {i} 行：01 66 25 81 0D 14 1B 22 29 30" for i in range(40))


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def host(qapp):
    window = QWidget()
    window.resize(900, 600)
    window.show()
    window.activateWindow()
    qapp.processEvents()
    yield window
    # 清理：关掉所有还开着、叠着或排队的弹框（有的可能已经随窗口销毁）
    stale_items = list(dialogs._stack) + list(dialogs._queue)
    dialogs._stack.clear()
    dialogs._queue.clear()
    for stale in stale_items:
        if isValid(stale) and not stale._done:
            stale._finish(None)
    if isValid(window):
        window.close()


def _text(overlay, name: str) -> str:
    return overlay.card.findChild(QLabel, name).text()


def _button_labels(overlay) -> list[str]:
    return [b.text() for b in overlay.buttons]


def _line_count(doc) -> int:
    """文档按当前宽度排版后的总行数（含块内折行）"""
    total, block = 0, doc.firstBlock()
    while block.isValid():
        if block.layout() is not None:
            total += block.layout().lineCount()
        block = block.next()
    return total


def _press_key(key: int):
    """模拟一次真实按键：系统先把按键交给窗口，窗口再转给当前持有焦点的控件。

    QTest.keyClick 在这个版本里把事件直接发给顶层窗口，不会转到焦点控件，所以不用它。
    """
    target = QApplication.focusWidget()
    assert target is not None, "当前没有控件持有焦点"
    QApplication.sendEvent(target, QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))


def _click_later(button: int, delay_ms: int = 30):
    """delay_ms 毫秒后，点击当时显示着的弹框的第 button 个按钮"""
    QTimer.singleShot(delay_ms, lambda: dialogs._current.buttons[button].click())


def _press_later(key: int, delay_ms: int = 30):
    QTimer.singleShot(delay_ms, lambda: _press_key(key))


class TestNotify:
    def test_covers_window_and_shows_plain_text(self, host):
        """遮罩铺满窗口；标题和说明按纯文本显示，内容里的标记字符不被解析。"""
        overlay = dialogs.warning(host, "<b>设备名称</b>不能为空", "请填写 <名称> 后再保存。")
        assert overlay.isVisible()
        assert overlay.geometry() == host.rect()
        assert _text(overlay, "dlg-title") == "<b>设备名称</b>不能为空"
        assert _text(overlay, "dlg-msg") == "请填写 <名称> 后再保存。"
        assert overlay.card.findChild(QLabel, "dlg-title").textFormat() == Qt.TextFormat.PlainText
        assert _button_labels(overlay) == ["确定"]

    @pytest.mark.parametrize(
        "close,expected",
        [
            ("button", True),      # 主按钮：带出 True
            ("enter", True),       # 焦点在主按钮上按回车
            ("escape", None),      # Esc 等同关闭
            ("scrim", None),       # 点遮罩
            ("close_icon", None),  # 右上角 ×
        ],
    )
    def test_notification_closes(self, host, close, expected):
        overlay = dialogs.success(host, "保存成功", "已保存到本地。")
        results = []
        overlay.finished.connect(results.append)
        if close == "button":
            overlay.buttons[-1].click()
        elif close == "enter":
            assert QApplication.focusWidget() is overlay.buttons[-1], "打开后焦点应在主按钮上"
            _press_key(Qt.Key.Key_Return)
        elif close == "escape":
            _press_key(Qt.Key.Key_Escape)
        elif close == "scrim":
            QTest.mouseClick(overlay, Qt.MouseButton.LeftButton, pos=QPoint(3, 3))
        else:
            overlay._close.click()
        assert results == [expected], f"通过 {close} 关闭弹框，结果应为 {expected}"

    def test_detail_adds_copy_button_and_keeps_dialog_open(self, host):
        overlay = dialogs.error(host, "连接失败", "无法连接 COM3。", detail="端口被占用")
        assert _button_labels(overlay) == ["复制", "关闭"]
        overlay.buttons[0].click()
        assert QApplication.clipboard().text() == "端口被占用"
        assert overlay.isVisible(), "点「复制」不应关闭弹框"

    def test_reveal_adds_open_folder_button(self, host):
        overlay = dialogs.success(host, "保存成功", "已保存。", detail="D:\\tmp\\a.txt", reveal="D:\\tmp\\a.txt")
        assert _button_labels(overlay) == ["复制", "打开目录", "确定"]
        assert overlay.detail.toPlainText() == "D:\\tmp\\a.txt"

    def test_detail_height_fits_content(self, host):
        """内容短：不出滚动条；内容长：封顶并可滚动。"""
        short = dialogs.info(host, "信息", detail="只有一行")
        assert short.detail.verticalScrollBar().maximum() == 0
        short._finish(None)

        long = dialogs.info(host, "报告", detail=LONG_REPORT)
        assert long.detail.height() == 163
        assert long.detail.verticalScrollBar().maximum() > 0

    def test_shown_detail_is_sized_for_its_real_wrap(self, host):
        """显示出来之后的详情区：折行数和量高度时预期的一致，所以不会冒出滚动条。

        回归：量高度时把宽度算宽了 2px、高度又差了不到 1px，显示后多折出一行并出现滚动条。
        （不断言具体几行：离屏环境没有字体文件，折行数和真实桌面不同。）
        """
        path = os.path.join(
            "D:\\04_AI_worksapce", "03_plantform", "vibeCoding-host-platform",
            "vibe-hmi", "history", "serial_log_2026-11-26_101641.txt",
        )
        overlay = dialogs.success(host, "保存成功", "已保存到本地。", detail=path, reveal=path)
        QApplication.processEvents()
        assert overlay.detail.width() == 470 - 48 - 2
        # 不应出现纵向滚动条占位
        assert overlay.detail.viewport().width() == overlay.detail.width() - 26
        measure = QTextDocument()
        measure.setDefaultFont(overlay.detail.font())
        measure.setPlainText(path)
        measure.setTextWidth(overlay.detail.viewport().width())
        measure.size()  # 取一次尺寸才会排版，之后才有行数
        assert _line_count(overlay.detail.document()) == _line_count(measure)
        assert overlay.detail.verticalScrollBar().maximum() == 0

    def test_enter_in_detail_triggers_default_button(self, host):
        overlay = dialogs.error(host, "失败", detail="详情")
        results = []
        overlay.finished.connect(results.append)
        overlay.detail.setFocus()
        _press_key(Qt.Key.Key_Return)
        assert results == [True], "焦点在详情区时按回车，应触发默认按钮"

    def test_follows_window_resize_and_stays_centered(self, host):
        overlay = dialogs.info(host, "信息")
        host.resize(1100, 700)
        QApplication.processEvents()
        assert overlay.geometry() == host.rect()
        card = overlay.card.geometry()
        assert abs(card.center().x() - overlay.width() / 2) <= 1
        assert abs(card.center().y() - overlay.height() / 2) <= 1

    def test_tab_stays_inside_dialog(self, host):
        overlay = dialogs.error(host, "失败", detail="详情")  # 焦点环：详情区 → 复制 → 关闭
        ring = overlay._focusables
        overlay.buttons[-1].setFocus()
        seen = []
        for _ in range(len(ring) + 2):
            _press_key(Qt.Key.Key_Tab)
            seen.append(QApplication.focusWidget())
        assert all(w in ring for w in seen), "Tab 把焦点带到了遮罩下面"
        assert seen[0] is ring[0], "从最后一个按钮按 Tab 应绕回第一个"


class TestConfirm:
    def test_returns_true_when_ok_clicked(self, host):
        _click_later(1)
        assert dialogs.confirm(host, "清理日志？", "将清理本地日志。") is True

    def test_returns_false_when_cancel_clicked(self, host):
        _click_later(0)
        assert dialogs.confirm(host, "清理日志？") is False

    def test_returns_false_on_escape(self, host):
        _press_later(Qt.Key.Key_Escape)
        assert dialogs.confirm(host, "清理日志？") is False

    def test_enter_confirms_normal_dialog(self, host):
        _press_later(Qt.Key.Key_Return)
        assert dialogs.confirm(host, "清理日志？") is True

    def test_enter_cancels_danger_dialog_by_default(self, host):
        _press_later(Qt.Key.Key_Return)
        assert dialogs.confirm(host, "删除 2 个设备？", danger=True) is False

    def test_normal_confirm_buttons(self, host):
        seen = {}

        def inspect():
            overlay = dialogs._current
            seen["labels"] = _button_labels(overlay)
            seen["focus_is_ok"] = QApplication.focusWidget() is overlay.buttons[1]
            overlay.buttons[1].click()

        QTimer.singleShot(30, inspect)
        assert dialogs.confirm(host, "清理日志？", ok_text="开始清理") is True
        assert seen["labels"] == ["取消", "开始清理"]
        assert seen["focus_is_ok"], "普通确认框打开时焦点应在主按钮上"

    def test_danger_confirm_is_safe_by_default(self, host):
        """危险确认：没有关闭按钮，红字提示不可恢复，点遮罩不关闭，默认焦点在"取消"。"""
        seen = {}

        def inspect():
            overlay = dialogs._current
            seen["close_button"] = overlay._close
            seen["danger_note"] = _text(overlay, "dlg-danger")
            seen["role"] = overlay.buttons[1].property("role")
            seen["focus_is_cancel"] = QApplication.focusWidget() is overlay.buttons[0]
            QTest.mouseClick(overlay, Qt.MouseButton.LeftButton, pos=QPoint(3, 3))
            seen["still_open_after_scrim_click"] = overlay.isVisible()
            overlay.buttons[0].click()

        QTimer.singleShot(30, inspect)
        assert dialogs.confirm(host, "删除 2 个设备？", "将删除…", danger=True, irreversible=True,
                               ok_text="删除") is False
        assert seen["close_button"] is None
        assert seen["danger_note"] == "此操作不可恢复。"
        assert seen["role"] == "danger"
        assert seen["still_open_after_scrim_click"] is True
        assert seen["focus_is_cancel"]


class TestQueue:
    def test_second_dialog_waits_for_first(self, host):
        first = dialogs.warning(host, "第一个")
        second = dialogs.info(host, "第二个")
        assert first.isVisible() and not second.isVisible()
        first.buttons[-1].click()
        assert second.isVisible()
        assert dialogs._current is second

    def test_confirm_stacks_on_open_notification(self, host):
        """已有通知开着时调用确认框：确认框叠在它上面立刻出现。

        确认框可能是从一个开着的弹框里发起的（如表单上再确认一次），排队会互相等待。
        """
        first = dialogs.info(host, "先看这个")
        seen = {}

        def inspect():
            seen["top"] = dialogs._current
            seen["first_still_visible"] = first.isVisible()
            dialogs._current.buttons[1].click()

        QTimer.singleShot(30, inspect)
        assert dialogs.confirm(host, "继续？") is True
        assert seen["top"] is not first
        assert seen["first_still_visible"]
        assert dialogs._current is first and first.isVisible(), "确认框关掉后应回到下面的通知"

    def test_notification_waits_while_custom_dialog_open(self, host, qapp):
        """自定义弹框（卡片里放表单内容）开着时，通知排队；自定义弹框带回调的按钮不会自己关。"""
        form = QWidget()
        field = QLineEdit(form)
        overlay = dialogs.DialogOverlay(
            host, dialogs.QUESTION, "自定义弹框", "卡片里放了一个输入框。", content=form,
            actions=(dialogs.Action("取消", "secondary", None, False),
                     dialogs.Action("确定", "primary", None, "确定结果")),
            default=field, closable=False, cancel_result=False,
        )
        assert overlay.card.isAncestorOf(field)
        assert overlay._default_focus is field, "default 给控件时，打开后焦点落在它上面"

        def inspect():
            # 自定义弹框开着的时候来了一条通知：应排队，不叠上来
            later.append(dialogs.warning(host, "排在后面的通知"))
            seen.append(later[0].isVisible())
            seen.append(QApplication.focusWidget() is field)
            dialogs._current.buttons[1].click()

        later, seen = [], []
        QTimer.singleShot(30, inspect)
        assert dialogs.run(overlay) == "确定结果"
        assert seen == [False, True], "弹框开着时通知不可见、焦点在内容区的控件上"
        qapp.processEvents()
        assert later[0].isVisible(), "自定义弹框关掉后，排队中的通知才显示"

    def test_enter_in_content_widget_is_not_intercepted(self, host):
        """焦点在自定义内容区的控件上按回车：不拦，也不触发默认按钮。"""
        form = QWidget()
        field = QLineEdit(form)
        overlay = dialogs.DialogOverlay(
            host, dialogs.QUESTION, "自定义弹框", content=form,
            actions=(dialogs.Action("确定", "primary", None, True),), default=field,
        )
        results = []
        overlay.finished.connect(results.append)
        field.setFocus()
        _press_key(Qt.Key.Key_Return)
        assert results == [], "内容区里的回车不应触发按钮"
        assert QApplication.focusWidget() in overlay._focusables


class TestTeardown:
    def test_destroyed_on_next_loop_turn_even_if_wrappers_collected(self, qapp):
        """回归：在事件回调里关闭后，宿主窗口和弹框的 Python 对象都被回收，销毁随后才执行。

        原先用 deleteLater：延迟删除排在 Python 对象被回收之后才执行时，
        PySide6 6.11 会访问冲突（整个进程崩溃）。测试收尾和程序退出时就是这个顺序。
        """
        window = QWidget()
        window.resize(600, 400)
        window.show()
        window.activateWindow()
        qapp.processEvents()
        overlay = dialogs.success(window, "标题", "说明")
        alive = weakref.ref(overlay)
        QTimer.singleShot(0, overlay.buttons[-1].click)  # 在事件回调里关闭，和真实点击一样
        qapp.processEvents()
        window.close()
        del overlay, window
        gc.collect()
        assert alive() is not None, "销毁之前必须保住弹框的 Python 引用"
        qapp.processEvents()  # 这里执行销毁
        gc.collect()
        assert alive() is None, "销毁之后弹框的 Python 对象应被释放"

    def test_stale_dialogs_are_dropped_when_host_destroyed(self, host, qapp):
        """宿主窗口被销毁：开着的弹框和排队的弹框都失效，之后的弹框照常显示，不会卡住。"""
        dialogs.info(host, "开着的时候窗口没了")
        dialogs.info(host, "排着队的时候窗口没了")
        other = QWidget()
        other.resize(500, 400)
        other.show()
        other.activateWindow()
        delete(host)  # 立即销毁（deleteLater 的事件在顶层 processEvents 里不会被处理）
        qapp.processEvents()
        current = dialogs.warning(other, "新窗口上的弹框")
        qapp.processEvents()
        assert current.isVisible() and dialogs._current is current
        assert not dialogs._queue
        current._finish(None)
        other.close()

    def test_blocking_confirm_returns_when_host_destroyed(self, host, qapp):
        """确认框开着的时候宿主窗口被销毁：阻塞的调用返回"未确认"，不会一直等下去。"""
        QTimer.singleShot(30, lambda: delete(host))
        assert dialogs.confirm(host, "继续？") is False
