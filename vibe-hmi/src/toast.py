"""
右下角轻提示

用于不需要用户处理的简短反馈（如"已删除 3 条报警记录"）：默认 2.5 秒后自动消失，
不打断操作。可以带一个操作（如"查看"）。鼠标停在提示上时不消失。

和弹框一样是主窗口的子控件，多条同时出现时堆在右下角，最新的在最下面。

用法：
    from .. import toast

    toast.show(self, "已删除 3 条报警记录")                       # 默认成功
    toast.show(self, "参数地址重复，未能保存", kind=toast.WARNING, action_text="查看", on_action=self.show)
"""
from shiboken6 import delete, isValid
from PySide6.QtCore import (
    QEvent, QObject, QPointF, QRectF, Qt, QPropertyAnimation, QTimer,
)
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter
from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QPushButton, QWidget

SUCCESS, INFO, WARNING = "success", "info", "warning"
DEFAULT_DURATION_MS = 2500

_DOT = {SUCCESS: "#34c38a", INFO: "#5aa0d8", WARNING: "#e5a53c"}
_PAD = 16               # 四周留给阴影的余量
_MARGIN_RIGHT = 20      # 距窗口右边缘
_MARGIN_BOTTOM = 16     # 距窗口底边（有状态栏时是距状态栏）
_GAP = 10               # 多条之间的间距
_FADE_IN_MS, _FADE_OUT_MS = 160, 200
_BODY_H = 40

_ACTION_QSS = """
QPushButton#toast-action {
    border: none; background: transparent; color: #8fc3ea;
    font-family: "Microsoft YaHei"; font-size: 13px; font-weight: 700;
    padding: 0 4px; min-height: 0; min-width: 0;
}
QPushButton#toast-action:hover {
    color: #c4e0f7; text-decoration: underline;
}
"""


def resolve_window(parent) -> QWidget | None:
    """弹层（弹框 / 轻提示）要盖住的那个窗口：调用方所在的最外层窗口。

    调用方还没进窗口（或在没有活动窗口时调用），退到当前活动窗口或任意可见窗口。
    """
    win = parent.window() if parent is not None else None
    if win is None or not win.isVisible():
        win = QApplication.activeWindow()
    if win is None:
        visible = [w for w in QApplication.topLevelWidgets() if w.isVisible()]
        win = visible[0] if visible else None
    return win


class Toast(QWidget):
    """一条轻提示：深色圆角条 + 状态圆点 + 文字（+ 可选操作）"""

    def __init__(self, host: QWidget, text: str, kind: str, action_text: str | None,
                 on_action, duration_ms: int):
        super().__init__(host)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 圆角和阴影外是透明的
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._text = text
        self._kind = kind
        self._on_action = on_action
        self._closing = False

        font = QFont("Microsoft YaHei")
        font.setPixelSize(13)
        self._font = font
        metrics = QFontMetricsF(font)
        text_w = metrics.horizontalAdvance(text)
        # 文字基线：相对提示条中心定位
        self._baseline = _BODY_H / 2 - metrics.height() / 2 + metrics.ascent()
        action_w = 0
        self._action_btn: QPushButton | None = None
        if action_text:
            bold = QFont(font)
            bold.setBold(True)
            action_w = QFontMetricsF(bold).horizontalAdvance(action_text) + 8  # 含按钮左右内边距
            btn = QPushButton(action_text)
            btn.setObjectName("toast-action")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 轻提示不抢键盘焦点
            btn.setStyleSheet(_ACTION_QSS)
            btn.clicked.connect(self._run_action)
            self._action_btn = btn
        body_w = 14 + 8 + 10 + text_w + ((16 + action_w) if action_text else 0) + 14
        self._body = QRectF(_PAD, _PAD, body_w, _BODY_H)
        self.setFixedSize(int(body_w) + 2 * _PAD, _BODY_H + 2 * _PAD)
        if self._action_btn is not None:
            self._action_btn.setParent(self)
            self._action_btn.setGeometry(
                int(self._body.left() + 14 + 8 + 10 + text_w + 16 - 4), _PAD + 6, int(action_w), _BODY_H - 12,
            )

        # 淡入 / 淡出
        self._opacity = QGraphicsOpacityEffect()
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._anim = QPropertyAnimation(self._opacity, b"opacity", self)
        self._anim.setDuration(_FADE_IN_MS)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(duration_ms)
        self._timer.timeout.connect(self.dismiss)
        self._timer.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(14, 0, -1):  # 投影：逐层向外变淡
            p.setBrush(QColor(22, 34, 51, 3))
            p.drawRoundedRect(self._body.adjusted(-i * 0.5, 5 - i * 0.2, i * 0.5, 7 + i * 0.8), 10, 10)
        p.setBrush(QColor(23, 32, 44, 242))  # 取自设计令牌 TOAST_BG #17202c
        p.drawRoundedRect(self._body, 8, 8)
        p.setBrush(QColor(_DOT[self._kind]))
        p.drawEllipse(QPointF(self._body.left() + 18, self._body.center().y()), 4, 4)
        p.setPen(QColor("#f5f7fa"))
        p.setFont(self._font)
        p.drawText(QPointF(self._body.left() + 14 + 8 + 10, self._body.top() + self._baseline), self._text)

    def enterEvent(self, event):
        self._timer.stop()  # 鼠标停在提示上：先不消失

    def leaveEvent(self, event):
        if not self._closing:
            self._timer.start()

    def _run_action(self):
        if self._on_action is not None:
            self._on_action()
        self.dismiss()

    def dismiss(self):
        """淡出后移除"""
        if self._closing:
            return
        self._closing = True
        self._timer.stop()
        self._anim.stop()
        self._anim.setDuration(_FADE_OUT_MS)
        self._anim.setStartValue(self._opacity.opacity())
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._remove)
        self._anim.start()

    def _remove(self):
        if self in _active:
            _active.remove(self)
        self.hide()
        # 真正销毁放到事件循环的下一轮：现在还在动画的结束信号里，不能直接删。
        # 不用 deleteLater：延迟删除事件可能排在 Python 对象被回收之后才执行，
        # PySide6 6.11 在这种顺序下会访问冲突。单次定时器持有 self 的引用，保证它活到销毁那一刻。
        QTimer.singleShot(0, self._destroy)
        _relayout(self.parentWidget())

    def _destroy(self):
        if isValid(self):
            delete(self)


_active: list[Toast] = []


class _Anchor(QObject):
    """宿主窗口大小变化时，重新摆放所有轻提示"""

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize:
            _relayout(watched)
        return False


_anchor = _Anchor()


def _prune():
    """把已经失效的轻提示从列表里去掉（宿主窗口被销毁时，它上面的轻提示会跟着销毁）"""
    _active[:] = [item for item in _active if isValid(item)]


def _relayout(host):
    if host is None or not isValid(host):
        return
    _prune()
    bottom = host.height() - _MARGIN_BOTTOM
    bar = host.statusBar() if hasattr(host, "statusBar") else None
    if bar is not None and bar.isVisible():
        bottom -= bar.height()
    for item in reversed(_active):  # 最新的在最下面
        if item.parentWidget() is not host:
            continue
        item.move(int(host.width() - _MARGIN_RIGHT - item._body.width() - _PAD),
                  int(bottom - item._body.height() - _PAD))
        bottom -= item._body.height() + _GAP


def show(parent, text: str, kind: str = SUCCESS, action_text: str | None = None,
         on_action=None, duration_ms: int = DEFAULT_DURATION_MS) -> Toast | None:
    """在调用方所在窗口的右下角弹出一条轻提示。

    kind：success / info / warning。action_text 与 on_action 同时给时带一个操作按钮。
    没有可用窗口时静默返回 None。
    """
    if not text:
        return None
    host = resolve_window(parent)
    if host is None or not isValid(host):
        return None
    _prune()
    host.installEventFilter(_anchor)
    item = Toast(host, text, kind, action_text, on_action, duration_ms)
    _active.append(item)
    _relayout(host)
    item.show()
    item.raise_()
    return item
