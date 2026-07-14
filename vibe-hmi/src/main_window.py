"""
主窗口

布局：QMainWindow 原生标题栏 + 原生菜单栏 + central widget（工具栏+工作区）+ 原生状态栏。

 grill-me 共识：去掉 HTML 原型的"桌面窗口模拟"层（desktop-window/假标题栏/边框圆角），
 改用系统原生标题栏/菜单栏/状态栏，避免"窗口套窗口"的视觉。
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QComboBox, QSizePolicy,
)
from PySide6.QtCore import Qt
from . import theme
from .store import store
from .page_registry import PAGES, get_page
from .sidebar import Sidebar
from .main_area import MainArea
from .pages.placeholder import PlaceholderPage
from .pages.params_page import ParamsPage
from .pages.monitor_page import MonitorPage


class MainWindow(QMainWindow):
    """上位机主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("multi-protocol-hmi")
        self.resize(1220, 760)
        self.setMinimumSize(900, 560)
        self._build_menu()
        self._build_statusbar()
        self._build_central()
        self._sync_monitor_tag()  # 启动时同步侧边栏"实时监控"标签

    def _sync_monitor_tag(self):
        """同步侧边栏"实时监控"标签为当前采样参数数量"""
        count = len(store.sample_params())
        self.sidebar.update_tag("monitor", f"{count} 点", "ok" if count > 0 else "warn")

    def _build_menu(self):
        """原生菜单栏：文件/连接/设备/数据/工具/帮助"""
        menubar = self.menuBar()
        for name in ["文件", "连接", "设备", "数据", "工具", "帮助"]:
            menubar.addMenu(name)

    def _build_central(self):
        """central widget：工具栏（上）+ 工作区（下，弹性）"""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 工具栏（固定高度，不拉伸）
        layout.addWidget(self._build_toolbar())
        # 工作区（弹性拉伸）
        layout.addWidget(self._build_workspace(), 1)

    def _build_toolbar(self):
        """工具栏：两行（控件行 + 状态行）

        布局太定制（5 下拉 + 2 按钮 + 状态行），用自定义 QFrame 而非原生 QToolBar。
        """
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        tlayout = QVBoxLayout(toolbar)
        tlayout.setContentsMargins(10, 8, 10, 8)
        tlayout.setSpacing(6)

        # --- 控件行 ---
        controls = QHBoxLayout()
        controls.setSpacing(8)

        controls.addWidget(self._make_tool_group("串口", ["COM3", "COM4", "COM5"]))
        controls.addWidget(self._make_tool_group("波特率", ["115200", "9600", "57600"]))
        controls.addWidget(self._make_tool_group("数据位", ["8 bit", "7 bit", "6 bit", "5 bit"]))
        controls.addWidget(self._make_tool_group("校验位", ["None", "Even", "Odd"]))
        controls.addWidget(self._make_tool_group("停止位", ["1 bit", "1.5 bit", "2 bit"]))

        self.btn_connect = QPushButton("断开")
        self.btn_refresh = QPushButton("刷新串口")
        self.btn_refresh.setProperty("variant", "secondary")
        controls.addWidget(self.btn_connect)
        controls.addWidget(self.btn_refresh)
        controls.addStretch()
        tlayout.addLayout(controls)

        # --- 状态行 ---
        stats = QHBoxLayout()
        stats.setSpacing(12)

        self.lbl_conn = QLabel("COM3 已连接")
        self.lbl_conn.setObjectName("stat-ok")
        self.lbl_rx = QLabel("RX 12,486 B")
        self.lbl_tx = QLabel("TX 1,024 B")
        self.lbl_crc = QLabel("CRC 0")
        self.lbl_ai = QLabel("AI 未配置")
        self.lbl_ai.setObjectName("stat-warn")

        for lbl in [self.lbl_conn, self.lbl_rx, self.lbl_tx, self.lbl_crc, self.lbl_ai]:
            stats.addWidget(lbl)
        stats.addStretch()
        tlayout.addLayout(stats)

        return toolbar

    def _make_tool_group(self, label_text, items):
        """工具栏的一个 label + 下拉组合"""
        group = QFrame()
        layout = QHBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setObjectName("tool-label")
        combo = QComboBox()
        combo.addItems(items)
        combo.setMinimumWidth(80 if len(items) <= 4 else 100)

        layout.addWidget(label)
        layout.addWidget(combo)
        group.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return group

    def _build_workspace(self):
        """工作区：侧边栏 + 主区（含页面路由）"""
        ws = QFrame()
        ws.setObjectName("workspace")
        lay = QHBoxLayout(ws)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 侧边栏
        self.sidebar = Sidebar()
        self.sidebar.page_clicked.connect(self.show_page)
        lay.addWidget(self.sidebar)

        # 主区（tabs + 内容）
        self.main_area = MainArea()
        self.main_area.page_clicked.connect(self.show_page)
        lay.addWidget(self.main_area, 1)

        # 注册所有页面
        # 已实现的页面用真实 widget，其余用占位
        ticket_map = {
            "overview": "票07", "serial": "票06", "monitor": "票05",
            "statusPolicy": "票07", "alarms": "票07",
            "history": "票08", "settings": "票07", "aiAssistant": "票09",
            "modelConfig": "票09",
        }
        for page in PAGES:
            if page.page_id == "params":
                widget = ParamsPage()
                # 表单 dirty 状态 → 同步侧边栏标签
                widget.dirty_changed.connect(
                    lambda dirty: self.sidebar.update_tag(
                        "params",
                        "未保存" if dirty else "已同步",
                        "warn" if dirty else "ok",
                    )
                )
                # 参数表保存/删除后 → 刷新监控页（采样参数增删联动）
                widget.dirty_changed.connect(self._on_params_maybe_changed)
            elif page.page_id == "monitor":
                widget = MonitorPage()
            else:
                widget = PlaceholderPage(page.name, ticket_map.get(page.page_id, ""))
            self.main_area.add_page(page.page_id, widget)
            if page.page_id == "monitor":
                self.monitor_page = widget

        # 默认显示首页
        self.show_page("overview")
        return ws

    def show_page(self, page_id: str):
        """路由：切换页面，联动侧边栏 active、tabs、状态栏"""
        meta = get_page(page_id)
        if not meta:
            return
        self.sidebar.set_active_page(page_id)
        self.main_area.show_page(page_id)
        # 状态栏当前页
        self.lbl_current_page.setText(meta.name)
        self._current_page_id = page_id

    def _on_params_maybe_changed(self, dirty: bool):
        """参数表 dirty 变为 False（保存/删除完成）时刷新监控页

        只在 dirty→False 的边沿触发（即真正的写盘动作），
        避免用户在表单里输入时频繁重建。
        """
        if dirty:
            return
        mp = getattr(self, "monitor_page", None)
        if mp:
            mp.refresh_params()
        self._sync_monitor_tag()

    def _build_statusbar(self):
        """原生状态栏"""
        sb = self.statusBar()
        sb.setObjectName("statusbar")
        left = QLabel("保存路径：./save | 配置：config.example.json | 当前用户：工程师")
        self.lbl_current_page = QLabel("首页/总览")
        sb.addWidget(left)
        sb.addPermanentWidget(self.lbl_current_page)
