"""
主区

迁移自原型 .main-area（tabs 行 + content 区）。
tabs 行显示所有页面标签（横向滚动），内容区用 QStackedWidget 切换。
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from . import theme
from .page_registry import PAGES


class MainArea(QFrame):
    """主区：tabs 行 + 内容区（QStackedWidget）

    继承 QFrame（而非 QWidget）以确保 QSS background 可靠填充。
    """

    # 点击 tab 时发射 page_id
    page_clicked = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("main-area")
        self._tab_buttons: dict[str, QPushButton] = {}  # page_id → tab 按钮
        self._stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}  # page_id → widget
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # tabs 行（横向滚动）
        tabs_scroll = QScrollArea()
        tabs_scroll.setObjectName("tabs-scroll")
        tabs_scroll.setWidgetResizable(True)
        tabs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tabs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tabs_scroll.setFixedHeight(40)

        tabs_widget = QWidget()
        tabs_widget.setObjectName("tabs")
        tabs_layout = QHBoxLayout(tabs_widget)
        tabs_layout.setContentsMargins(8, 6, 8, 0)
        tabs_layout.setSpacing(2)
        tabs_layout.addStretch()

        for page in PAGES:
            tab_btn = QPushButton(page.name)
            tab_btn.setObjectName("tab")
            tab_btn.setCheckable(True)
            tab_btn.setFlat(True)
            tab_btn.clicked.connect(lambda checked=False, pid=page.page_id: self.page_clicked.emit(pid))
            tabs_layout.insertWidget(tabs_layout.count() - 1, tab_btn)  # 插到 stretch 前
            self._tab_buttons[page.page_id] = tab_btn

        tabs_scroll.setWidget(tabs_widget)
        layout.addWidget(tabs_scroll)

        # 内容区（QStackedWidget）
        layout.addWidget(self._stack, 1)

    def add_page(self, page_id: str, widget: QWidget):
        """注册一个页面的内容 widget 到 stack"""
        self._pages[page_id] = widget
        self._stack.addWidget(widget)

    def show_page(self, page_id: str):
        """切换到指定页面：更新 tab active + stack 当前 widget"""
        # 更新 tab
        for pid, btn in self._tab_buttons.items():
            btn.setChecked(pid == page_id)
        # 切换 stack
        if page_id in self._pages:
            self._stack.setCurrentWidget(self._pages[page_id])
