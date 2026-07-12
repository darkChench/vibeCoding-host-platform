"""
侧边栏

迁移自原型 .sidebar（230px 固定宽 + pane-title + tree）。
三组（设备/数据/AI）的树导航，点击切换页面，active 态高亮。
点击时发射 page_clicked 信号，由 main_window 接收并调路由切换。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy,
)
from PySide6.QtCore import Signal
from . import theme
from .page_registry import PAGES, GROUPS, PageMeta


class TreeItem(QPushButton):
    """单个树导航项（图标 + 名称 + 标签）"""

    def __init__(self, meta: PageMeta):
        super().__init__()
        self.page_id = meta.page_id
        self.setObjectName("tree-item")
        self.setCheckable(False)
        self.setFlat(True)
        self.setText(f"  {meta.icon}  {meta.name}{'          ' + meta.tag if meta.tag else ''}")
        self.setProperty("tag_type", meta.tag_type)

    def set_active(self, active: bool):
        """设置 active 态（高亮）"""
        self.setProperty("active", "true" if active else "false")
        self.style().polish(self)  # 刷新 QSS


class Sidebar(QWidget):
    """侧边栏：pane-title + 三组树导航"""

    # 点击树项时发射 page_id
    page_clicked = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(230)
        self._items: dict[str, TreeItem] = {}  # page_id → TreeItem
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # pane-title（"项目导航"）
        pane_title = QLabel("项目导航")
        pane_title.setObjectName("pane-title")
        layout.addWidget(pane_title)

        # tree（三组）
        tree = QWidget()
        tree.setObjectName("tree")
        tree_layout = QVBoxLayout(tree)
        tree_layout.setContentsMargins(10, 10, 10, 10)
        tree_layout.setSpacing(0)

        for group in GROUPS:
            # 分组标题（"设备"/"数据"/"AI"）
            heading = QLabel(group.upper())
            heading.setObjectName("tree-heading")
            tree_layout.addWidget(heading)
            tree_layout.addSpacing(6)

            # 该组下的所有页面
            for page in PAGES:
                if page.group != group:
                    continue
                item = TreeItem(page)
                item.clicked.connect(lambda checked=False, pid=page.page_id: self.page_clicked.emit(pid))
                self._items[page.page_id] = item
                tree_layout.addWidget(item)
                tree_layout.addSpacing(2)

            tree_layout.addSpacing(12)

        tree_layout.addStretch()
        layout.addWidget(tree, 1)

    def set_active_page(self, page_id: str):
        """高亮指定页面（其他取消高亮）"""
        for pid, item in self._items.items():
            item.set_active(pid == page_id)
