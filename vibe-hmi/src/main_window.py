"""
主窗口：5 行 grid 框架

迁移自原型 layout.css 的 .desktop-window（grid-template-rows: 34 34 auto 1fr 28）。
行1 标题栏 / 行2 菜单栏 / 行3 工具栏（两行：控件+状态）/ 行4 工作区（弹性）/ 行5 状态栏。

工作区（票02填充侧边栏+页面路由）暂时放占位 widget。
工具栏下拉暂时放占位（票02/06填充真实串口配置）。
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QFrame, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QSizePolicy,
)
from PySide6.QtCore import Qt
from . import theme


class MainWindow(QMainWindow):
    """上位机主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("multi-protocol-hmi")
        self.resize(1220, 760)
        self.setMinimumSize(900, 560)
        self._build_ui()

    def _build_ui(self):
        """构建 5 行 grid 框架"""
        central = QWidget()
        self.setCentralWidget(central)

        # 外层：桌面窗体容器（圆角+边框，对应 .desktop-window）
        desktop = QFrame()
        desktop.setObjectName("desktop-window")
        desktop_layout = QGridLayout(desktop)
        desktop_layout.setContentsMargins(0, 0, 0, 0)
        desktop_layout.setSpacing(0)

        # 5 行 grid：标题栏 / 菜单栏 / 工具栏 / 工作区 / 状态栏
        # 行3（工具栏）最小高度50，行4（工作区）弹性拉伸
        desktop_layout.setRowStretch(0, 0)  # 标题栏 固定
        desktop_layout.setRowStretch(1, 0)  # 菜单栏 固定
        desktop_layout.setRowStretch(2, 0)  # 工具栏 固定（auto）
        desktop_layout.setRowStretch(3, 1)  # 工作区 弹性
        desktop_layout.setRowStretch(4, 0)  # 状态栏 固定

        desktop_layout.addWidget(self._build_titlebar(), 0, 0)
        desktop_layout.addWidget(self._build_menubar(), 1, 0)
        desktop_layout.addWidget(self._build_toolbar(), 2, 0)
        desktop_layout.addWidget(self._build_workspace(), 3, 0)
        desktop_layout.addWidget(self._build_statusbar(), 4, 0)

        # 外层 layout（留边距，模拟原型的 .shell padding:18px）
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.addWidget(desktop)

    def _build_titlebar(self):
        """行1 标题栏：app 图标 + 名称 | 居中副标题 | 三圆点"""
        bar = QFrame()
        bar.setObjectName("titlebar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(12)

        # 左：app 图标方块 + 名称
        icon = QFrame()
        icon.setFixedSize(18, 18)
        icon.setStyleSheet(f"background: {theme.HEX['PRIMARY']}; border-radius: 4px;")
        app_label = QLabel("multi-protocol-hmi")
        app_label.setObjectName("titlebar-app")
        layout.addWidget(icon)
        layout.addWidget(app_label)

        # 中：居中副标题（弹性占位让标题居中）
        layout.addStretch()
        center = QLabel("Windows 上位机 - 首页/总览")
        center.setObjectName("titlebar-center")
        center.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(center)
        layout.addStretch()

        # 右：三圆点（模拟窗口按钮）
        for color in [theme.WINBTN_MIN, theme.WINBTN_MAX, theme.WINBTN_CLOSE]:
            dot = QFrame()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background: {color.name()}; border-radius: 5px;")
            layout.addWidget(dot)

        return bar

    def _build_menubar(self):
        """行2 菜单栏：文件/连接/设备/数据/工具/帮助"""
        bar = QFrame()
        bar.setObjectName("menubar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)

        for name in ["文件", "连接", "设备", "数据", "工具", "帮助"]:
            btn = QPushButton(name)
            btn.setObjectName("menu-item")
            btn.setFlat(True)
            layout.addWidget(btn)
        layout.addStretch()

        return bar

    def _build_toolbar(self):
        """行3 工具栏：两行（控件行 + 状态行）

        控件行：串口/波特率/数据位/校验位/停止位 下拉 + 连接/刷新 按钮
        状态行：COM 状态 / RX / TX / CRC / AI 状态
        """
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        layout = QVBoxLayout(toolbar)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # --- 控件行 ---
        controls = QHBoxLayout()
        controls.setSpacing(8)

        # 串口配置下拉（占位，票06 接真实串口枚举）
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
        layout.addLayout(controls)

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
            lbl.setObjectName(lbl.objectName() or "stats-strip")
            stats.addWidget(lbl)
        stats.addStretch()
        layout.addLayout(stats)

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
        """行4 工作区（票02 填充侧边栏+路由，暂占位）"""
        ws = QFrame()
        ws.setObjectName("workspace")
        placeholder = QLabel("工作区（票02 实现侧边栏+页面路由）")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color: {theme.HEX['MUTED']}; font-size: {theme.FS_LG}pt;")
        lay = QHBoxLayout(ws)
        lay.addWidget(placeholder)
        return ws

    def _build_statusbar(self):
        """行5 状态栏"""
        bar = QFrame()
        bar.setObjectName("statusbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)

        left = QLabel("保存路径：./save | 配置：config.example.json | 当前用户：工程师")
        left.setObjectName("statusbar-text")
        self.lbl_current_page = QLabel("首页/总览")
        self.lbl_current_page.setObjectName("statusbar-text")

        layout.addWidget(left)
        layout.addStretch()
        layout.addWidget(self.lbl_current_page)
        return bar
