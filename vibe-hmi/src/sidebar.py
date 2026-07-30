"""
侧边栏

迁移自原型 .sidebar（230px 固定宽 + pane-title + tree）。
三组（设备/数据/AI）的树导航，点击切换页面，active 态高亮。

TreeItem 用 QFrame 三列布局（图标 | 名称 | 标签），精确对齐，
对应原型 .tree-item 的 grid-template-columns: 18px 1fr auto。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QSizePolicy,
    QPushButton, QSpacerItem,
)
from PySide6.QtCore import Signal, Qt, QEvent
from . import theme
from .icons import get_icon_pixmap, get_active_icon_pixmap
from .page_registry import PAGES, GROUPS, PageMeta

# 展开宽度（默认）与收起宽度（仅留标题栏，可点击展开）
EXPANDED_WIDTH = 230
COLLAPSED_WIDTH = 44


class TreeItem(QFrame):
    """单个树导航项：三列布局（图标 | 名称 | 标签），点击切换页面"""

    def __init__(self, meta: PageMeta):
        super().__init__()
        self.page_id = meta.page_id
        self.setObjectName("tree-item")
        self.setProperty("active", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        # 列1：图标（SVG 渲染成 QPixmap）
        self.icon_label = QLabel()
        self.icon_label.setObjectName("tree-icon")
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setPixmap(get_icon_pixmap(meta.icon, size=20))

        # 列2：名称（弹性）
        self.name_label = QLabel(meta.name)
        self.name_label.setObjectName("tree-name")

        # 列3：标签（右对齐，如"3"/"COM3"/"2 点"）
        self.tag_label = QLabel(meta.tag) if meta.tag else QLabel("")
        self.tag_label.setObjectName("tree-tag")
        if meta.tag_type == "ok":
            self.tag_label.setProperty("variant", "ok")
        elif meta.tag_type == "warn":
            self.tag_label.setProperty("variant", "warn")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label, 1)
        layout.addWidget(self.tag_label)

        self._hovered = False

    def enterEvent(self, event):
        """hover 态"""
        self._hovered = True
        self.setProperty("hovered", "true")
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """离开 hover"""
        self._hovered = False
        self.setProperty("hovered", "false")
        self.style().polish(self)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        """点击释放时触发切换"""
        if event.button() == Qt.MouseButton.LeftButton and self._hovered:
            # 找到父 Sidebar 发射信号
            parent = self.parent()
            while parent and not isinstance(parent, Sidebar):
                parent = parent.parent()
            if parent:
                parent.page_clicked.emit(self.page_id)
        super().mouseReleaseEvent(event)

    def set_active(self, active: bool):
        """设置 active 态（高亮）：切换图标颜色 + QSS 高亮"""
        self.setProperty("active", "true" if active else "false")
        # 用 page_id 查 meta 拿 icon key，再按 active 态选颜色渲染
        from .page_registry import get_page
        meta = get_page(self.page_id)
        if meta:
            if active:
                self.icon_label.setPixmap(get_active_icon_pixmap(meta.icon, size=20))
            else:
                self.icon_label.setPixmap(get_icon_pixmap(meta.icon, size=20))
        self.style().polish(self)


class Sidebar(QFrame):
    """侧边栏：pane-title（含折叠按钮）+ 三组树导航

    继承 QFrame 确保 QSS background 可靠填充。
    支持点击折叠按钮收起/展开：收起时仅留标题栏，按钮显示 >；展开时按钮显示 <。
    """

    page_clicked = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(EXPANDED_WIDTH)
        self._items: dict[str, TreeItem] = {}
        self._collapsed = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # pane-title：横向布局（标题 + 折叠按钮）
        # 按钮通过 addStretch 固定在右侧，收起时文字隐藏，stretch 自动收缩
        # 但按钮仍贴右（与展开态 < 同一水平位置）
        pane_title = QFrame()
        pane_title.setObjectName("pane-title")
        pane_title.setFixedHeight(38)  # 固定标题栏高度，收起时 tree 隐藏也不会被拉高
        pt_layout = QHBoxLayout(pane_title)
        pt_layout.setContentsMargins(12, 0, 4, 0)
        pt_layout.setSpacing(4)

        self.title_label = QLabel("项目导航")
        self.title_label.setObjectName("pane-title-text")
        pt_layout.addWidget(self.title_label)
        # 用 QSpacerItem 而非 addStretch（addStretch 在 PySide6 返回 None，无法后续操控）
        self.title_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        pt_layout.addSpacerItem(self.title_spacer)

        # 折叠按钮：展开时显示 <（点击收起），收起时显示 >（点击展开）
        self.collapse_btn = QPushButton("<")
        self.collapse_btn.setObjectName("sidebar-collapse-btn")
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn.setFixedSize(28, 28)
        self.collapse_btn.setToolTip("收起侧边栏")
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        pt_layout.addWidget(self.collapse_btn)

        self.pane_title = pane_title  # 保存引用，切换收起态时调整布局
        self.pt_layout = pt_layout
        # AlignTop：收起时 tree 隐藏，pane_title 仍固定在顶部（不被居中）
        layout.addWidget(pane_title, 0, Qt.AlignmentFlag.AlignTop)

        # tree（三组）
        self.tree_container = QWidget()
        self.tree_container.setObjectName("tree")
        tree_layout = QVBoxLayout(self.tree_container)
        tree_layout.setContentsMargins(10, 10, 10, 10)
        tree_layout.setSpacing(0)

        for group in GROUPS:
            heading = QLabel(group.upper())
            heading.setObjectName("tree-heading")
            tree_layout.addWidget(heading)
            tree_layout.addSpacing(6)

            for page in PAGES:
                if page.group != group:
                    continue
                item = TreeItem(page)
                self._items[page.page_id] = item
                tree_layout.addWidget(item)
                tree_layout.addSpacing(2)

            tree_layout.addSpacing(12)

        tree_layout.addStretch()
        layout.addWidget(self.tree_container, 1)

    def toggle_collapse(self):
        """切换收起/展开状态"""
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool):
        """设置收起/展开状态

        展开时按钮 < 贴右（标题文字 + spacer弹性 + 按钮）；
        收起时隐藏标题文字并把 spacer 设为 0 宽，让按钮 > 仍贴右，
        与展开态按钮在同一水平位置（标题栏右侧）。
        """
        self._collapsed = collapsed
        if collapsed:
            self.setFixedWidth(COLLAPSED_WIDTH)
            self.tree_container.setVisible(False)
            self.title_label.setVisible(False)
            # spacer 收缩为 0，按钮贴右（与展开态 < 同位置）
            self.title_spacer.changeSize(0, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
            self.pt_layout.invalidate()
            self.collapse_btn.setText(">")
            self.collapse_btn.setToolTip("展开侧边栏")
        else:
            self.setFixedWidth(EXPANDED_WIDTH)
            self.tree_container.setVisible(True)
            self.title_label.setVisible(True)
            # spacer 恢复弹性，把按钮推到右侧
            self.title_spacer.changeSize(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            self.pt_layout.invalidate()
            self.collapse_btn.setText("<")
            self.collapse_btn.setToolTip("收起侧边栏")

    def set_active_page(self, page_id: str):
        """高亮指定页面（其他取消高亮）"""
        for pid, item in self._items.items():
            item.set_active(pid == page_id)

    def update_tag(self, page_id: str, text: str, tag_type: str = ""):
        """动态更新某页面的右侧标签（text + 颜色类型）

        tag_type: "" 默认 / "ok" 绿 / "warn" 橙
        """
        item = self._items.get(page_id)
        if not item:
            return
        item.tag_label.setText(text)
        item.tag_label.setProperty("variant", tag_type)
        item.tag_label.style().polish(item.tag_label)
