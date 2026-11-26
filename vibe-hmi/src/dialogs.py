"""
应用内弹框

盖在主窗口上的遮罩 + 居中卡片，用来替换系统自带的 QMessageBox：
系统弹框的标题栏、图标、按钮都不受样式表控制，和应用的卡片风格不搭。

实现上不是独立的系统窗口，而是主窗口的子控件：
- 遮罩盖住整个窗口（含菜单栏和状态栏），挡住下面的鼠标操作
- 焦点限制在卡片内部，Tab 不会跑到遮罩下面
- 圆角和阴影都是普通控件绘制（无边框透明窗口在 Windows 上有圆角外发黑的问题）

结构：左侧状态图标，右侧自上而下是粗体标题、说明、补充说明、只读详情区，按钮在右下。
同一时间只显示一个通知类弹框；前一个没关时，后面的通知排队，关掉后依次出现。
确认框和自定义弹框（run）不排队，直接叠在已有弹框上面。

用法：
    from .. import dialogs

    dialogs.warning(self, "设备名称不能为空", "请填写设备名称后再保存。")       # 不阻塞
    dialogs.success(self, "保存成功", "已保存到本地。", detail=path, reveal=path)
    if not dialogs.confirm(self, "删除 2 个设备？", "…", danger=True, irreversible=True):
        return                                                               # 阻塞，返回是否确认

文案惯例：标题说"是什么事"，说明说"该怎么办"；失败类把技术细节放进 detail。
所有文字按纯文本显示（内容里有 < > & 不会被当成标记）。
"""
import math
import os
from collections import deque
from collections import namedtuple

from shiboken6 import delete, isValid
from PySide6.QtCore import (
    Qt, QEvent, QEventLoop, QPoint, QPointF, QRectF, QTimer, Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QTextDocument
from PySide6.QtWidgets import (
    QApplication, QGraphicsDropShadowEffect, QFrame, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from .toast import resolve_window, show as _show_toast

SUCCESS, INFO, WARNING, DANGER, QUESTION = "success", "info", "warning", "danger", "question"

# 状态图标：(浅色圆底, 图形色)
_ICON = {
    SUCCESS: ("#e8f6ef", "#11875d"),
    INFO: ("#e9f4ff", "#0b6fb3"),
    QUESTION: ("#e9f4ff", "#0b6fb3"),
    WARNING: ("#fff4df", "#b86b00"),
    DANGER: ("#fdecec", "#bf3a46"),
}
# 遮罩色取自原型 --modal-scrim：rgba(15,23,42,.42)
_SCRIM = QColor(15, 23, 42, 107)
# 详情区字体：与下面样式表里的 dlg-detail 保持一致（量高度时要用同一个字体）
_DETAIL_FONT = QFont("Consolas", 9)

# 弹框按钮：text 按钮文字；role primary / secondary / danger；
# callback 不为 None 时点击只执行回调、不关闭弹框；result 是点击后弹框带出的结果
Action = namedtuple("Action", "text role callback result")

_QSS = """
QFrame#dlg-card {
    background: #ffffff; border-radius: 8px; border: 1px solid #e3e9f0;
}
QLabel#dlg-title {
    color: #17202c; font-size: 11pt; font-weight: 700; background: transparent;
}
QLabel#dlg-msg {
    color: #405066; font-size: 10pt; font-weight: 400; background: transparent;
}
QLabel#dlg-note {
    color: #617083; font-size: 9pt; font-weight: 400; background: transparent;
}
QLabel#dlg-danger {
    color: #bf3a46; font-size: 10pt; font-weight: 400; background: transparent;
}
QPlainTextEdit#dlg-detail {
    background: #f7f9fc; color: #243b53;
    border: 1px solid #e6ecf3; border-radius: 6px; padding: 9px 12px;
    font-family: Consolas, "Cascadia Mono", "Courier New", monospace;
    font-size: 9pt; font-weight: 400;
    selection-background-color: #cfe3f5; selection-color: #17202c;
}
QPushButton#dlg-btn {
    min-height: 34px; min-width: 84px; padding: 0 18px; border-radius: 6px;
    font-size: 10pt; font-weight: 700;
}
QPushButton#dlg-btn[role="primary"] {
    background: #0b6fb3; border: 1px solid #0b6fb3; color: #ffffff;
}
QPushButton#dlg-btn[role="secondary"] {
    background: #ffffff; border: 1px solid #c3cedb; color: #17202c;
}
QPushButton#dlg-btn[role="danger"] {
    background: #bf3a46; border: 1px solid #bf3a46; color: #ffffff;
}
QPushButton#dlg-btn[role="primary"]:hover {
    background: #0a66a3; border-color: #0a66a3;
}
QPushButton#dlg-btn[role="primary"]:pressed {
    background: #07588e; border-color: #07588e;
}
QPushButton#dlg-btn[role="secondary"]:hover {
    background: #f3f6fa; border-color: #aeb9c8;
}
QPushButton#dlg-btn[role="secondary"]:pressed {
    background: #e8eef5; border-color: #aeb9c8;
}
QPushButton#dlg-btn[role="danger"]:hover {
    background: #ad323d; border-color: #ad323d;
}
QPushButton#dlg-btn[role="danger"]:pressed {
    background: #9f2632; border-color: #9f2632;
}
/* 键盘焦点：按钮内侧一圈描边，不改变按钮尺寸 */
QPushButton#dlg-btn[role="primary"]:focus {
    border: 2px solid #9fcbec; padding: 0 17px;
}
QPushButton#dlg-btn[role="danger"]:focus {
    border: 2px solid #efb3b8; padding: 0 17px;
}
QPushButton#dlg-btn[role="secondary"]:focus {
    background: #f3f8fd; border: 2px solid #0b6fb3; padding: 0 17px;
}
QPushButton#dlg-close {
    border: none; background: transparent; border-radius: 6px;
    min-height: 0; min-width: 0; padding: 0;
}
QPushButton#dlg-close:hover {
    background: #eef2f7;
}
"""


def _label(text: str, name: str) -> QLabel:
    """纯文本标签：不解析内容里的标记字符"""
    lbl = QLabel(text)
    lbl.setObjectName(name)
    lbl.setTextFormat(Qt.TextFormat.PlainText)
    lbl.setWordWrap(True)
    return lbl


class _StatusIcon(QWidget):
    """状态图标：浅色圆底 + 状态色线条图形（矢量绘制，缩放也清晰）"""

    def __init__(self, kind: str, size: int = 40):
        super().__init__()
        self._kind = kind
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        s = self.width()
        c = s / 2
        tint, fg = _ICON[self._kind]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(tint))
        p.drawEllipse(QPointF(c, c), s / 2 - 0.5, s / 2 - 0.5)
        color = QColor(fg)
        pen = QPen(color, 2.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if self._kind == SUCCESS:
            path = QPainterPath(QPointF(c - 6.4, c + 0.4))
            path.lineTo(c - 1.9, c + 4.9)
            path.lineTo(c + 6.8, c - 4.6)
            p.drawPath(path)
        elif self._kind == DANGER:
            k = 5.4
            p.drawLine(QPointF(c - k, c - k), QPointF(c + k, c + k))
            p.drawLine(QPointF(c + k, c - k), QPointF(c - k, c + k))
        elif self._kind == WARNING:
            p.drawLine(QPointF(c, c - 6.4), QPointF(c, c + 1.6))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawEllipse(QPointF(c, c + 6.5), 1.5, 1.5)
        elif self._kind == INFO:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawEllipse(QPointF(c, c - 5.4), 1.7, 1.7)
            pen.setWidthF(2.8)
            p.setPen(pen)
            p.drawLine(QPointF(c, c - 1.0), QPointF(c, c + 6.6))
        else:  # QUESTION
            font = QFont("Microsoft YaHei")
            font.setPixelSize(22)
            font.setBold(True)
            path = QPainterPath()
            path.addText(0, 0, font, "?")
            box = path.boundingRect()
            p.translate(c - box.center().x(), c - box.center().y() - 0.5)
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(path)


class _CloseButton(QPushButton):
    """右上角的关闭按钮：底图由样式表画（含悬停底色），自己只画一个 ×"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dlg-close")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoDefault(False)
        self.setFixedSize(28, 28)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#617083"), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        c, k = self.width() / 2, 4.2
        p.drawLine(QPointF(c - k, c - k), QPointF(c + k, c + k))
        p.drawLine(QPointF(c + k, c - k), QPointF(c - k, c + k))


class DialogOverlay(QWidget):
    """遮罩层：盖住整个宿主窗口，中央是卡片"""

    finished = Signal(object)  # 关闭时带出结果：按钮对应的 result，关闭/取消为 cancel_result

    def __init__(self, host: QWidget, kind: str, title: str, message: str = "", *, note: str = "",
                 danger_note: str = "", detail: str | None = None, content: QWidget | None = None,
                 actions: tuple = (), default: int | QWidget = 0, closable: bool = True,
                 cancel_result=None, width: int = 460, detail_max_h: int = 163):
        super().__init__(host)
        self._host = host
        self._closable = closable
        self._cancel_result = cancel_result
        self._result = None
        self._done = False            # 是否已经关闭
        self._focusables: list[QWidget] = []   # Tab 只在这些控件之间循环
        self._prev_focus = None
        self.setStyleSheet(_QSS)

        # 卡片是遮罩的子控件，位置手工摆放（居中），不参与布局
        self.card = QFrame(self)
        self.card.setObjectName("dlg-card")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(22, 34, 51, 120))
        self.card.setGraphicsEffect(shadow)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(0)

        # 头部：状态图标 + 文字列（标题 / 说明 / 补充说明 / 不可恢复提示）
        head = QHBoxLayout()
        head.setSpacing(14)
        head.setContentsMargins(0, 0, 34 if closable else 0, 0)  # 右上角给关闭按钮留位
        icon_col = QVBoxLayout()
        icon_col.setContentsMargins(0, 3, 0, 0)  # 图标下移 3px，对准文字块的视觉中心
        icon_col.addWidget(_StatusIcon(kind))
        head.addLayout(icon_col)
        col = QVBoxLayout()
        col.setContentsMargins(0, 1, 0, 0)
        col.setSpacing(6)
        for text, name in ((title, "dlg-title"), (message, "dlg-msg"),
                           (note, "dlg-note"), (danger_note, "dlg-danger")):
            if text:
                col.addWidget(_label(text, name))
        head.addLayout(col, 1)
        root.addLayout(head)
        if closable:
            self._close = _CloseButton(self.card)
            self._close.clicked.connect(lambda: self._finish(cancel_result))
        else:
            self._close = None

        # 只读详情区：路径、报文、错误原因；可选中复制，内容多时滚动
        self.detail: QPlainTextEdit | None = None
        if detail:
            edit = QPlainTextEdit()
            edit.setObjectName("dlg-detail")
            edit.setReadOnly(True)
            edit.setPlainText(detail)
            edit.setTabChangesFocus(True)
            edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)  # 自动换行，不出横向滚动条
            edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            # 高度按换行后的真实排版算。控件没显示之前它自己的排版器不出结果，
            # 所以用临时文档按同样的字体和可用宽度排一遍（结果含文档边距 8），再加内边距和边框 20。
            # 可用宽度 = 卡片宽 − 左右外边距 48 − 卡片边框 2 − 详情区内边距 24 − 详情区边框 2
            # （必须和实际一致，否则换个宽度会多折一行）
            measure = QTextDocument()
            measure.setDefaultFont(_DETAIL_FONT)
            measure.setPlainText(detail)
            measure.setTextWidth(width - 76)
            # 向上取整并留 2px：行高带小数时，刚好相等的高度会差出 1px 而冒出一条滚动条
            need = math.ceil(measure.size().height()) + 22
            edit.setFixedHeight(min(detail_max_h, need))
            edit.installEventFilter(self)  # 拦截 Tab / 回车
            root.addSpacing(14)
            root.addWidget(edit)
            self.detail = edit
            self._focusables.append(edit)

        # 自定义内容区：放表单等（如"删除历史数据"里选设备和时间范围）
        if content is not None:
            root.addSpacing(16)
            root.addWidget(content)
            # 内容区里能获得焦点的控件也纳入 Tab 循环，顺序排在按钮之前
            for widget in content.findChildren(QWidget):
                if widget.focusPolicy() != Qt.FocusPolicy.NoFocus:
                    widget.installEventFilter(self)
                    self._focusables.append(widget)

        # 底部：按钮靠右
        root.addSpacing(22)
        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addStretch()
        self.buttons: list[QPushButton] = []
        for action in actions:
            btn = QPushButton(action.text)
            btn.setObjectName("dlg-btn")
            btn.setProperty("role", action.role)
            btn.setFixedHeight(34)
            btn.setMinimumWidth(84)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setAutoDefault(False)  # Enter 只触发当前有焦点的按钮
            btn.installEventFilter(self)  # 拦截 Tab / 回车
            btn.clicked.connect(lambda checked=False, a=action: self._on_action(a))
            footer.addWidget(btn)
            self.buttons.append(btn)
            self._focusables.append(btn)
        root.addLayout(footer)

        # 宽度固定，高度按内容算：先让布局按这个宽度排一遍，再取内容高度
        self.card.setFixedWidth(width)
        self.card.layout().activate()
        self.card.setFixedSize(width, max(self.card.sizeHint().height(),
                                          self.card.minimumSizeHint().height()))
        if self._close is not None:
            self._close.move(self.card.width() - 14 - self._close.width(), 12)

        # 默认焦点：default 是控件就落在它上面；是序号就落在对应的按钮上
        if isinstance(default, QWidget):
            self._default_focus = default
        else:
            first = len(self._focusables) - len(actions)
            self._default_focus = self._focusables[first + default]

    # ===== 显示与关闭 =====

    def open(self):
        """盖到宿主窗口上，并把焦点交给默认按钮"""
        self._prev_focus = QApplication.focusWidget()
        self._host.installEventFilter(self)
        self.setGeometry(self._host.rect())
        self._place_card()
        self.raise_()
        self.show()
        self._default_focus.setFocus(Qt.FocusReason.OtherFocusReason)

    def _place_card(self):
        self.card.move((self.width() - self.card.width()) // 2,
                       (self.height() - self.card.height()) // 2)

    def _on_action(self, action: Action):
        if action.callback is not None:
            action.callback()  # 复制、打开目录这类操作：执行后弹框留着
            return
        self._finish(action.result)

    def _finish(self, result):
        if self._done:
            return
        self._done = True
        self._result = result
        self._host.removeEventFilter(self)
        previous = self._prev_focus
        self.hide()
        # 真正销毁放到事件循环的下一轮：现在可能还在按钮的事件处理过程中，不能直接删。
        # 不用 deleteLater：延迟删除事件可能排在 Python 对象被回收之后才执行，
        # PySide6 6.11 在这种顺序下会访问冲突（测试收尾、程序退出时会出现）。
        # 单次定时器持有 self 的引用，保证 Python 对象一定活到销毁那一刻。
        QTimer.singleShot(0, self._destroy)
        if previous is not None:
            try:
                previous.setFocus(Qt.FocusReason.OtherFocusReason)  # 焦点还给打开弹框前的控件
            except RuntimeError:
                pass  # 弹框开着的时候那个控件已经被销毁了
        self.finished.emit(result)

    def _destroy(self):
        if isValid(self):
            delete(self)

    # ===== 事件 =====

    def paintEvent(self, event):
        QPainter(self).fillRect(self.rect(), _SCRIM)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_card()

    def mousePressEvent(self, event):
        # 点在遮罩上：通知类等同关闭；确认类必须明确选一个按钮
        if self._closable:
            self._finish(self._cancel_result)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._finish(self._cancel_result)
        else:
            event.ignore()

    def eventFilter(self, watched, event):
        kind = event.type()
        if watched is self._host:
            if kind == QEvent.Type.Resize:  # 宿主窗口大小变了：遮罩跟着铺满，卡片保持居中
                self.setGeometry(self._host.rect())
                self._place_card()
            return False
        # 焦点只在卡片内部循环：Tab / Shift+Tab 不会跑到遮罩下面的控件
        if kind == QEvent.Type.KeyPress and watched in self._focusables:
            key = event.key()
            shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            if key == Qt.Key.Key_Tab and not shift:
                self._move_focus(1)
                return True
            if key == Qt.Key.Key_Backtab or (key == Qt.Key.Key_Tab and shift):
                self._move_focus(-1)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                # 弹框不是 QDialog，按钮不会自动响应回车，这里手动触发：
                # 焦点在按钮上就点它；焦点在只读详情区就点默认按钮。
                # 自定义内容区里的控件不拦，交给它们自己处理
                if isinstance(watched, QPushButton):
                    watched.click()
                    return True
                if watched is self.detail:
                    if isinstance(self._default_focus, QPushButton):
                        self._default_focus.click()
                    return True
        return super().eventFilter(watched, event)

    def _move_focus(self, step: int):
        ring = self._focusables
        index = ring.index(QApplication.focusWidget()) if QApplication.focusWidget() in ring else 0
        ring[(index + step) % len(ring)].setFocus(Qt.FocusReason.TabFocusReason)


# ===== 对外接口 =====

_stack: list[DialogOverlay] = []          # 正在显示的弹框，从下到上，最后一个是当前弹框
_queue: deque[DialogOverlay] = deque()   # 等前面的弹框都关掉再显示的通知
_current: DialogOverlay | None = None     # 当前（最上面的）弹框，没有时为 None


def _sync_current():
    """清掉已关闭或已失效的弹框（宿主窗口被销毁时它们跟着销毁），刷新 _current"""
    global _current
    _stack[:] = [overlay for overlay in _stack if isValid(overlay) and not overlay._done]
    alive = [overlay for overlay in _queue if isValid(overlay)]
    _queue.clear()
    _queue.extend(alive)
    _current = _stack[-1] if _stack else None


def _push(overlay: DialogOverlay):
    """立刻显示，叠在已有弹框上面"""
    global _current
    overlay.finished.connect(_on_finished)
    _stack.append(overlay)
    _current = overlay
    overlay.open()


def _enqueue(overlay: DialogOverlay) -> DialogOverlay:
    """通知类弹框：有弹框开着就排队，都关掉之后按先后顺序显示"""
    _sync_current()
    if _current is not None:
        _queue.append(overlay)
    else:
        _push(overlay)
    return overlay


def _on_finished(_result):
    _sync_current()
    if _current is not None:
        return
    while _queue:  # 开着的弹框都关掉了：显示排队中的下一个通知
        nxt = _queue.popleft()
        if isValid(nxt):  # 宿主窗口已被销毁的弹框直接丢弃
            _push(nxt)
            break


def run(overlay: DialogOverlay):
    """显示一个自定义弹框并阻塞到它关闭（期间事件循环照常运行），返回它带出的结果。

    会叠在已有弹框的上面，例如在"删除历史数据"的表单上再叠一个二次确认。
    """
    _sync_current()
    _push(overlay)
    return _wait(overlay)


def _wait(overlay: DialogOverlay):
    """阻塞到弹框关闭（期间事件循环照常运行），返回结果。

    宿主窗口被销毁或应用退出时也会返回，不会一直等下去。
    """
    result = None
    if isValid(overlay):
        loop = QEventLoop()
        overlay.finished.connect(lambda value: loop.quit())
        overlay._host.destroyed.connect(loop.quit)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(loop.quit)
        if not overlay._done:
            loop.exec()
        result = overlay._result
    return result


def _copy(text: str):
    def run():
        QApplication.clipboard().setText(text)
        _show_toast(None, "已复制到剪贴板", kind=SUCCESS)
    return run


def _open_folder(path: str):
    def run():
        try:
            os.startfile(os.path.dirname(os.path.abspath(path)))
        except OSError as e:
            _show_toast(None, f"无法打开目录：{e}", kind=WARNING)
    return run


def _host_of(parent) -> QWidget:
    """弹框要盖住的窗口；没有任何可见窗口时无法显示，直接报错而不是变成独立窗口"""
    host = resolve_window(parent)
    if host is None:
        raise RuntimeError("没有可显示弹框的窗口")
    return host


def _notify(parent, kind: str, title: str, message: str = "", *, note: str = "", detail: str | None = None,
            reveal: str | None = None, ok_text: str = "确定") -> DialogOverlay:
    """通知类弹框（不阻塞）：有详情就带"复制"，给了路径就带"打开目录"，最后是主按钮"""
    actions = []
    if detail:
        actions.append(Action("复制", "secondary", _copy(detail), None))
    if reveal:
        actions.append(Action("打开目录", "secondary", _open_folder(reveal), None))
    actions.append(Action(ok_text, "primary", None, True))
    return _enqueue(DialogOverlay(
        _host_of(parent), kind, title, message, note=note, detail=detail,
        actions=tuple(actions), default=len(actions) - 1, closable=True,
        width=470 if reveal else 460,  # 带文件路径的稍宽一点，长路径少折一行
    ))


def success(parent, title: str, message: str = "", *, detail: str | None = None,
            reveal: str | None = None) -> DialogOverlay:
    """操作成功。detail 放结果详情；reveal 给文件路径时多一个"打开目录"按钮。"""
    return _notify(parent, SUCCESS, title, message, detail=detail, reveal=reveal)


def info(parent, title: str, message: str = "", *, detail: str | None = None) -> DialogOverlay:
    """一般信息。"""
    return _notify(parent, INFO, title, message, detail=detail)


def warning(parent, title: str, message: str = "") -> DialogOverlay:
    """需要用户处理才能继续的情况：表单校验不通过、操作的前提不满足。"""
    return _notify(parent, WARNING, title, message)


def error(parent, title: str, message: str = "", *, detail: str | None = None) -> DialogOverlay:
    """操作失败。message 写原因，detail 放技术细节（报文、异常信息）。"""
    return _notify(parent, DANGER, title, message, detail=detail, ok_text="关闭")


def confirm(parent, title: str, message: str = "", *, note: str = "", detail: str | None = None,
            irreversible: bool = False, danger: bool = False, ok_text: str = "确定",
            cancel_text: str = "取消") -> bool:
    """确认框（阻塞）：返回是否点了确认按钮。

    danger：主按钮红色，用于删除这类破坏性操作。
    irreversible：额外用红字提示"此操作不可恢复"。
    detail：需要用户过目的清单（如要删除的对象名称），放在只读详情区。
    danger 或 irreversible 为真时，打开后的焦点落在"取消"上；确认框没有关闭按钮，Esc 等同取消。
    """
    overlay = DialogOverlay(
        _host_of(parent), DANGER if danger else QUESTION, title, message, note=note, detail=detail,
        danger_note="此操作不可恢复。" if irreversible else "",
        actions=(Action(cancel_text, "secondary", None, False),
                 Action(ok_text, "danger" if danger else "primary", None, True)),
        default=0 if (danger or irreversible) else 1, closable=False, cancel_result=False,
        width=480 if danger else 460,  # 要列出删除对象的名称，稍宽一点免得句子折出孤字
    )
    # 叠在已有弹框上面，不排队：确认框可能是从一个开着的弹框里发起的，排队会互相等待
    return run(overlay) is True
