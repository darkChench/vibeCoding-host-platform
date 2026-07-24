"""
国网配置页

迁移自原型 js/pages/params.js（表单结构），但功能专化为"国网协议参数"读写。
单卡布局：card-head 标题"国网协议参数" + 右侧"读取"/"写入"按钮；
body 内 4 个参数：通信地址 / 波特率 / 奇偶校验位 / 日期时间。

读取：从串口/模拟读参数 → 回填表单。
写入：把表单值打包下发。
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFrame, QMessageBox, QGridLayout,
    QDateTimeEdit, QSizePolicy, QSpinBox, QScrollArea,
)
from PySide6.QtCore import Qt, QDateTime, Signal, QTimer
from PySide6.QtGui import QWheelEvent

from .. import theme
from ..serial.serial_manager import serial_manager


class NoWheelComboBox(QComboBox):
    """禁用鼠标滚轮修改的下拉框（防止误操作）"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class NoWheelLineEdit(QLineEdit):
    """禁用鼠标滚轮修改的输入框（防止误操作）"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class NoWheelDateTimeEdit(QDateTimeEdit):
    """禁用鼠标滚轮修改的日期时间框（防止误操作）"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class NoWheelSpinBox(QSpinBox):
    """禁用鼠标滚轮修改的数字框（防止误操作；上下箭头键仍可 +1/-1）"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class SensorStatusBox(QFrame):
    """单个传感器状态框：名称 + 状态背景色

    状态：normal（未采集，浅灰）/ ok（正常，绿底黑字）/ warn（异常，红底黑字）。
    背景色直接表达状态，无边框/角标。
    """

    def __init__(self, name: str):
        super().__init__()
        self.setObjectName("sensor-status-box")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(40)
        self._name = name

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(0)

        # 名称（居中，黑字）
        self._text = QLabel(name)
        self._text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text.setStyleSheet(
            "color: #000000; font-size: 10pt; "
            "font-weight: 800; background: transparent; border: none;"
        )
        lay.addWidget(self._text)

        self._apply_state("normal")

    def set_state(self, state: str):
        """更新状态：normal / ok / warn"""
        self._apply_state(state)

    def _apply_state(self, state: str):
        # 三档背景色：未采集=浅灰 / 正常=绿 / 异常=红
        bgs = {
            "normal": "#e8edf4",   # 浅灰
            "ok":     "#7ed4a3",   # 绿
            "warn":   "#ec8888",   # 红
        }
        bg = bgs.get(state, "#e8edf4")
        self.setStyleSheet(
            f"#sensor-status-box {{ border: none; "
            f"border-radius: {theme.RADIUS_SM}px; background: {bg}; }}"
        )


class RealtimeMetric(QFrame):
    """只读实时数据指标：标签 + 数值（带单位），样式复用监控页 metric 卡"""

    def __init__(self, name: str, display: str, unit: str, decimals: int = 2):
        super().__init__()
        self.setObjectName("metric")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(78)
        self._unit = unit
        self._decimals = decimals

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)

        self.label = QLabel(display or name)
        self.label.setObjectName("metric-label")
        self.value = QLabel("--")
        self.value.setObjectName("metric-value")
        self.value.setTextFormat(Qt.TextFormat.RichText)
        self.value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        lay.addWidget(self.label)
        lay.addWidget(self.value, 1)

    def set_value(self, value, ok: bool):
        """刷新数值（ok=False 或 None 时显示 --）"""
        muted = theme.HEX["MUTED"]
        if not ok or value is None:
            num = "--"
        else:
            num = f"{value:.{self._decimals}f}"
        self.value.setText(f'{num}<small><font color="{muted}"> {self._unit}</font></small>')


# 9 个传感器状态框的名称（顺序固定，UI 上按此顺序排列）
SENSOR_STATUS_NAMES = [
    "泄漏", "液化",
    "闭锁2接线", "闭锁1接线", "报警接线",
    "闭锁2动作", "闭锁1动作", "报警动作",
    "超压报警",
]

# 4 个实时数据项：name → (显示名, 单位, 小数位数)
REALTIME_METRICS = [
    ("density",  "密度值",   "kg/m³", 3),
    ("temp",     "温度值",   "℃",    1),
    ("pressure", "相对压力", "MPa",  3),
    ("water",    "微水",     "ppm",  2),
]

# 4 个阈值字段：name → 显示名
THRESHOLD_FIELDS = [
    ("alarm",   "报警节点阈值"),
    ("lock1",   "闭锁1阈值"),
    ("lock2",   "闭锁2阈值"),
    ("overpress", "超压节点阈值"),
]


# 波特率选项（value → 显示文案）
BAUD_RATES = [
    (0, "2400"),
    (1, "4800"),
    (2, "9600"),
    (3, "19200"),
]

# 奇偶校验位选项（value → 显示文案）
PARITY_OPTIONS = [
    (0, "无校验"),
    (1, "奇校验"),
    (2, "偶校验"),
]

# 版本标签选项（小写字母 a ~ z）
VERSION_LABELS = [chr(c) for c in range(ord("a"), ord("z") + 1)]

# 版本号选项（01 ~ 10）
VERSION_NUMBERS = [f"{n:02d}" for n in range(1, 11)]

# 产品序列号范围
SERIAL_MIN = 300001
SERIAL_MAX = 999999
SERIAL_DEFAULT = 600001


class GwConfigPage(QWidget):
    """国网配置页"""

    # 状态变化信号（供侧边栏标签联动）
    state_changed = Signal(bool)  # True=已同步 / False=未同步

    def __init__(self):
        super().__init__()
        self._build_ui()
        # 初始化默认时间 = 当前时间（精确到秒）
        self._reset_datetime_to_now()
        self._set_synced(True)
        self._set_device_synced(True)

    def _build_ui(self):
        """整页可滚动：通信 + 设备信息 + 传感器状态 + 实时数据 + 阈值设置 5 张卡片"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self._build_comm_card())
        layout.addWidget(self._build_device_card())
        layout.addWidget(self._build_sensor_status_card())
        layout.addWidget(self._build_realtime_data_card())
        layout.addWidget(self._build_threshold_card())
        layout.addStretch()  # 底部留白，卡片按内容高度紧凑排列

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # 默认所有自动采集都关闭
        self._auto_sensor = False
        self._auto_realtime = False
        self._sensor_timer = QTimer(self)
        self._sensor_timer.setInterval(1000)  # 1 秒一次
        self._sensor_timer.timeout.connect(self._on_sensor_tick)
        self._realtime_timer = QTimer(self)
        self._realtime_timer.setInterval(1000)
        self._realtime_timer.timeout.connect(self._on_realtime_tick)

    # ===== 字段组件（label 在上、input 在下，两卡共用）=====

    def _field(self, label_text: str, widget) -> QWidget:
        """label 在上、input 在下的紧凑字段组件"""
        f = QWidget()
        lay = QVBoxLayout(f)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            f"color: {theme.HEX['MUTED']}; font-size: {theme.FS_SM}pt; "
            f"font-weight: {theme.FW_BOLD};"
        )
        lay.addWidget(lbl)
        lay.addWidget(widget)
        return f

    # ===== 上卡：表计通信标识 =====

    def _build_comm_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # card-head：标题 + 同步状态 tag + 读取/写入按钮
        head = QFrame()
        head.setObjectName("card-head")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(10, 0, 10, 0)

        self.form_title = QLabel("表计通信标识")
        self.form_title.setObjectName("card-title")
        head_layout.addWidget(self.form_title)

        head_layout.addStretch()

        # 同步状态 tag（"已同步"/"未同步"）
        from .params_page import StatusChip
        self.state_tag = StatusChip("已同步", "ok")
        head_layout.addWidget(self.state_tag, alignment=Qt.AlignmentFlag.AlignVCenter)

        head_layout.addSpacing(12)

        # 读取 / 写入按钮
        self.btn_read = QPushButton("读取")
        self.btn_read.setProperty("variant", "secondary")
        self.btn_read.clicked.connect(self._on_read)
        head_layout.addWidget(self.btn_read, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.btn_write = QPushButton("写入")
        self.btn_write.clicked.connect(self._on_write)
        head_layout.addWidget(self.btn_write, alignment=Qt.AlignmentFlag.AlignVCenter)

        card_layout.addWidget(head)

        # body：表单（两列，label 在上 input 在下，紧凑不拉伸）
        body = QWidget()
        form = QGridLayout(body)
        form.setContentsMargins(14, 12, 14, 14)
        form.setVerticalSpacing(12)
        form.setHorizontalSpacing(12)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)

        # 字段 1：通信地址（QLineEdit，1-247）
        self.f_addr = NoWheelLineEdit()
        self.f_addr.setPlaceholderText("1 ~ 247")
        self.f_addr.setText("1")
        self.f_addr.setMaxLength(3)
        self.f_addr.textChanged.connect(self._on_form_changed)

        # 字段 2：波特率（QComboBox）
        self.f_baud = NoWheelComboBox()
        for value, label in BAUD_RATES:
            self.f_baud.addItem(f"{value}:{label}", value)
        self.f_baud.setCurrentIndex(2)  # 默认 9600
        self.f_baud.currentIndexChanged.connect(self._on_form_changed)

        # 字段 3：奇偶校验位（QComboBox）
        self.f_parity = NoWheelComboBox()
        for value, label in PARITY_OPTIONS:
            self.f_parity.addItem(f"{value}:{label}", value)
        self.f_parity.setCurrentIndex(0)  # 默认 无校验
        self.f_parity.currentIndexChanged.connect(self._on_form_changed)

        # 字段 4：日期时间（QDateTimeEdit，精确到秒，可编辑）
        self.f_datetime = NoWheelDateTimeEdit()
        self.f_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.f_datetime.setCalendarPopup(True)
        self.f_datetime.dateTimeChanged.connect(self._on_form_changed)
        self.f_datetime.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # 两列布局：第 1 列 → 通信地址、奇偶校验位；第 2 列 → 波特率、日期时间
        form.addWidget(self._field("通信地址", self.f_addr), 0, 0)
        form.addWidget(self._field("波特率", self.f_baud), 0, 1)
        form.addWidget(self._field("奇偶校验位", self.f_parity), 1, 0)
        form.addWidget(self._field("日期时间", self.f_datetime), 1, 1)

        card_layout.addWidget(body)  # 不加拉伸因子 → 卡片按内容高度紧凑
        return card

    # ===== 下卡：设备基本信息标识 =====

    def _build_device_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        head = QFrame()
        head.setObjectName("card-head")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(10, 0, 10, 0)

        title = QLabel("设备基本信息标识")
        title.setObjectName("card-title")
        head_layout.addWidget(title)

        head_layout.addStretch()

        from .params_page import StatusChip
        self.dev_state_tag = StatusChip("已同步", "ok")
        head_layout.addWidget(self.dev_state_tag, alignment=Qt.AlignmentFlag.AlignVCenter)

        head_layout.addSpacing(12)

        self.btn_dev_read = QPushButton("读取")
        self.btn_dev_read.setProperty("variant", "secondary")
        self.btn_dev_read.clicked.connect(self._on_read_device)
        head_layout.addWidget(self.btn_dev_read, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.btn_dev_write = QPushButton("写入")
        self.btn_dev_write.clicked.connect(self._on_write_device)
        head_layout.addWidget(self.btn_dev_write, alignment=Qt.AlignmentFlag.AlignVCenter)

        card_layout.addWidget(head)

        # body：两列表单
        body = QWidget()
        form = QGridLayout(body)
        form.setContentsMargins(14, 12, 14, 14)
        form.setVerticalSpacing(12)
        form.setHorizontalSpacing(12)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)

        # 字段 1：设备型号
        self.f_model = NoWheelLineEdit()
        self.f_model.setPlaceholderText("设备型号")
        self.f_model.textChanged.connect(self._on_device_form_changed)

        # 字段 2：厂商代码
        self.f_vendor = NoWheelLineEdit()
        self.f_vendor.setPlaceholderText("厂商代码")
        self.f_vendor.textChanged.connect(self._on_device_form_changed)

        # 字段 3：版本标签（小写字母 a ~ z）
        self.f_ver_label = NoWheelComboBox()
        self.f_ver_label.addItems(VERSION_LABELS)
        self.f_ver_label.setCurrentIndex(0)  # 默认 a
        self.f_ver_label.currentIndexChanged.connect(self._on_device_form_changed)

        # 字段 4：版本号（01 ~ 10）
        self.f_ver_num = NoWheelComboBox()
        self.f_ver_num.addItems(VERSION_NUMBERS)
        self.f_ver_num.setCurrentIndex(0)  # 默认 01
        self.f_ver_num.currentIndexChanged.connect(self._on_device_form_changed)

        # 字段 5：产品序列号（最低 300001，默认 600001，上下键 +1/-1）
        self.f_serial = NoWheelSpinBox()
        self.f_serial.setRange(SERIAL_MIN, SERIAL_MAX)
        self.f_serial.setSingleStep(1)
        self.f_serial.setValue(SERIAL_DEFAULT)
        self.f_serial.valueChanged.connect(self._on_device_form_changed)

        # 字段 6：表计 ID（H）（只读）
        self.f_meter_id_h = NoWheelLineEdit()
        self.f_meter_id_h.setReadOnly(True)
        self.f_meter_id_h.setPlaceholderText("自动生成（只读）")

        # 字段 7：表计 ID（D）（只读）
        self.f_meter_id_d = NoWheelLineEdit()
        self.f_meter_id_d.setReadOnly(True)
        self.f_meter_id_d.setPlaceholderText("自动生成（只读）")

        # 字段 8：传感器类型标识（只读）
        self.f_sensor_type = NoWheelLineEdit()
        self.f_sensor_type.setReadOnly(True)

        form.addWidget(self._field("设备型号", self.f_model), 0, 0)
        form.addWidget(self._field("厂商代码", self.f_vendor), 0, 1)
        form.addWidget(self._field("版本标签", self.f_ver_label), 1, 0)
        form.addWidget(self._field("版本号", self.f_ver_num), 1, 1)
        form.addWidget(self._field("产品序列号", self.f_serial), 2, 0)
        form.addWidget(self._field("表计ID（H）", self.f_meter_id_h), 2, 1)
        form.addWidget(self._field("表计ID（D）", self.f_meter_id_d), 3, 0)
        form.addWidget(self._field("传感器类型标识", self.f_sensor_type), 3, 1)

        card_layout.addWidget(body)
        return card

    # ===== 第三卡：传感器状态 =====

    def _build_sensor_status_card(self) -> QFrame:
        """第三卡：传感器状态

        head：标题 + 状态 chip + 自动采集按钮（toggle）
        body：
          - 第一行：左侧 "传感器状态" 标签 + 右侧一个状态圆点（默认红）
          - 第二行起：3×3 网格的 9 个 SensorStatusBox
        """
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # head
        head = QFrame()
        head.setObjectName("card-head")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(10, 0, 10, 0)

        title = QLabel("传感器状态")
        title.setObjectName("card-title")
        head_layout.addWidget(title)
        head_layout.addStretch()

        from .params_page import StatusChip
        self.sensor_state_tag = StatusChip("未采集", "warn")
        head_layout.addWidget(self.sensor_state_tag, alignment=Qt.AlignmentFlag.AlignVCenter)

        head_layout.addSpacing(12)

        self.btn_auto_sensor = QPushButton("自动采集")
        self.btn_auto_sensor.setProperty("variant", "secondary")
        self.btn_auto_sensor.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auto_sensor.clicked.connect(self._toggle_auto_sensor)
        head_layout.addWidget(self.btn_auto_sensor, alignment=Qt.AlignmentFlag.AlignVCenter)

        card_layout.addWidget(head)

        # body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 12, 14, 14)
        bl.setSpacing(10)

        # 第一行：标签 + 状态圆点 + "异常"/"正常" 文本（紧凑排列，靠左）
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        title_label = QLabel("传感器状态")
        title_label.setStyleSheet(
            f"color: {theme.HEX['TEXT']}; font-size: {theme.FS_MD}pt; "
            f"font-weight: {theme.FW_BOLD};"
        )
        row1.addWidget(title_label)
        self.sensor_main_dot = QLabel()
        self.sensor_main_dot.setFixedSize(14, 14)
        self.sensor_main_dot.setStyleSheet(
            f"background: {theme.HEX['DANGER']}; border-radius: 7px; border: none;"
        )
        row1.addWidget(self.sensor_main_dot)
        self.sensor_main_text = QLabel("异常")
        self.sensor_main_text.setStyleSheet(
            f"color: {theme.HEX['DANGER']}; font-size: {theme.FS_MD}pt; "
            f"font-weight: {theme.FW_BOLD};"
        )
        row1.addWidget(self.sensor_main_text)
        row1.addStretch()
        bl.addLayout(row1)

        # 第二行起：3×3 网格的 9 个状态框
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)
        self._sensor_boxes: list[SensorStatusBox] = []
        for i, name in enumerate(SENSOR_STATUS_NAMES):
            box = SensorStatusBox(name)
            self._sensor_boxes.append(box)
            r, c = divmod(i, 3)
            grid.addWidget(box, r, c)
        # 三列等宽
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        bl.addLayout(grid)

        card_layout.addWidget(body)
        return card

    # ===== 第四卡：实时数据 =====

    def _build_realtime_data_card(self) -> QFrame:
        """第四卡：实时数据（只读）

        head：标题 + 状态 chip + 自动采集按钮
        body：2×2 网格的 4 个 RealtimeMetric（密度值 / 温度值 / 相对压力 / 微水）
        """
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # head
        head = QFrame()
        head.setObjectName("card-head")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(10, 0, 10, 0)

        title = QLabel("实时数据")
        title.setObjectName("card-title")
        head_layout.addWidget(title)
        head_layout.addStretch()

        from .params_page import StatusChip
        self.realtime_state_tag = StatusChip("未采集", "warn")
        head_layout.addWidget(self.realtime_state_tag, alignment=Qt.AlignmentFlag.AlignVCenter)

        head_layout.addSpacing(12)

        self.btn_auto_realtime = QPushButton("自动采集")
        self.btn_auto_realtime.setProperty("variant", "secondary")
        self.btn_auto_realtime.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auto_realtime.clicked.connect(self._toggle_auto_realtime)
        head_layout.addWidget(self.btn_auto_realtime, alignment=Qt.AlignmentFlag.AlignVCenter)

        card_layout.addWidget(head)

        # body：2×2 metric 网格
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(14, 12, 14, 14)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self._realtime_metrics: dict[str, RealtimeMetric] = {}
        for i, (name, display, unit, decimals) in enumerate(REALTIME_METRICS):
            m = RealtimeMetric(name, display, unit, decimals)
            self._realtime_metrics[name] = m
            r, c = divmod(i, 2)
            grid.addWidget(m, r, c)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        card_layout.addWidget(body)
        return card

    # ===== 第五卡：阈值设置 =====

    def _build_threshold_card(self) -> QFrame:
        """第五卡：阈值设置

        head：标题 + 状态 chip + 读取/写入按钮
        body：2×2 输入字段：报警节点阈值 / 闭锁1阈值 / 闭锁2阈值 / 超压节点阈值
        """
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # head
        head = QFrame()
        head.setObjectName("card-head")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(10, 0, 10, 0)

        title = QLabel("阈值设置")
        title.setObjectName("card-title")
        head_layout.addWidget(title)
        head_layout.addStretch()

        from .params_page import StatusChip
        self.threshold_state_tag = StatusChip("已同步", "ok")
        head_layout.addWidget(self.threshold_state_tag, alignment=Qt.AlignmentFlag.AlignVCenter)

        head_layout.addSpacing(12)

        self.btn_thr_read = QPushButton("读取")
        self.btn_thr_read.setProperty("variant", "secondary")
        self.btn_thr_read.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_thr_read.clicked.connect(self._on_read_thresholds)
        head_layout.addWidget(self.btn_thr_read, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.btn_thr_write = QPushButton("写入")
        self.btn_thr_write.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_thr_write.clicked.connect(self._on_write_thresholds)
        head_layout.addWidget(self.btn_thr_write, alignment=Qt.AlignmentFlag.AlignVCenter)

        card_layout.addWidget(head)

        # body：2×2 输入字段
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(14, 12, 14, 14)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self._thr_fields: dict[str, NoWheelLineEdit] = {}
        for i, (name, display) in enumerate(THRESHOLD_FIELDS):
            edit = NoWheelLineEdit()
            edit.setPlaceholderText(display)
            edit.textChanged.connect(self._on_threshold_changed)
            self._thr_fields[name] = edit
            r, c = divmod(i, 2)
            grid.addWidget(self._field(display, edit), r, c)

        card_layout.addWidget(body)
        return card

    # ===== 时间辅助 =====

    def _reset_datetime_to_now(self):
        """把日期时间字段重置为当前时间（精确到秒）"""
        now = datetime.now()
        # 去掉微秒，保留整秒
        now = now.replace(microsecond=0)
        self.f_datetime.setDateTime(QDateTime(now))

    # ===== 状态 tag =====

    def _set_synced(self, synced: bool):
        """切换状态 tag + 发射信号"""
        if synced:
            self.state_tag.update_state("已同步", "ok")
        else:
            self.state_tag.update_state("未同步", "warn")
        self.state_changed.emit(synced)

    def _on_form_changed(self, *_args):
        """任一字段改动 → 标记未同步"""
        self._set_synced(False)

    # ===== 设备基本信息标识：状态 + 读写 =====

    def _set_device_synced(self, synced: bool):
        """切换设备信息卡状态 tag"""
        if synced:
            self.dev_state_tag.update_state("已同步", "ok")
        else:
            self.dev_state_tag.update_state("未同步", "warn")

    def _on_device_form_changed(self, *_args):
        """设备信息卡任一字段改动 → 标记未同步"""
        self._set_device_synced(False)

    def _set_device_fields(self, *, model: str, vendor: str,
                           ver_label: str, ver_num: str, serial: int):
        """程序填充设备信息字段（屏蔽信号，避免误触发未同步）"""
        line_widgets = [self.f_model, self.f_vendor]
        combos = [self.f_ver_label, self.f_ver_num]
        for w in line_widgets:
            w.blockSignals(True)
        for c in combos:
            c.blockSignals(True)
        self.f_serial.blockSignals(True)

        self.f_model.setText(model)
        self.f_vendor.setText(vendor)
        idx_label = VERSION_LABELS.index(ver_label) if ver_label in VERSION_LABELS else 0
        self.f_ver_label.setCurrentIndex(idx_label)
        idx_num = VERSION_NUMBERS.index(ver_num) if ver_num in VERSION_NUMBERS else 0
        self.f_ver_num.setCurrentIndex(idx_num)
        self.f_serial.setValue(max(SERIAL_MIN, min(SERIAL_MAX, serial)))
        # 表计 ID（H/D）只读，按序列号派生展示
        self.f_meter_id_h.setText(f"{serial:X}")
        self.f_meter_id_d.setText(str(serial))

        for w in line_widgets:
            w.blockSignals(False)
        for c in combos:
            c.blockSignals(False)
        self.f_serial.blockSignals(False)

    def _on_read_device(self):
        """从设备读取基本信息标识 → 回填表单"""
        if not serial_manager.is_connected:
            QMessageBox.warning(
                self, "读取失败",
                "串口未连接，无法读取设备基本信息。\n（演示模式将直接使用默认值）"
            )
            return
        try:
            # TODO: 真实协议解析后回填。下面用模拟值演示流程
            self._set_device_fields(
                model="DTZ188", vendor="0001",
                ver_label="a", ver_num="01", serial=SERIAL_DEFAULT,
            )
            self._set_device_synced(True)
            QMessageBox.information(self, "读取成功", "已从设备读取基本信息标识")
        except Exception as e:
            QMessageBox.warning(self, "读取失败", f"读取异常：{e}")

    def _on_write_device(self):
        """把设备基本信息标识写入设备"""
        model = self.f_model.text().strip()
        vendor = self.f_vendor.text().strip()
        ver_label = self.f_ver_label.currentText()
        ver_num = self.f_ver_num.currentText()
        serial = self.f_serial.value()

        if serial < SERIAL_MIN:
            QMessageBox.warning(
                self, "写入失败",
                f"产品序列号不能小于 {SERIAL_MIN}"
            )
            return

        if not serial_manager.is_connected:
            QMessageBox.warning(
                self, "写入失败",
                "串口未连接，无法写入设备信息。\n（演示模式将只显示待写入的值）"
            )
            QMessageBox.information(
                self, "待写入设备信息（演示）",
                f"设备型号：{model}\n"
                f"厂商代码：{vendor}\n"
                f"版本标签：{ver_label}\n"
                f"版本号：{ver_num}\n"
                f"产品序列号：{serial}"
            )
            return

        try:
            self.btn_dev_write.setText("写入中...")
            self.btn_dev_write.setEnabled(False)
            QTimer.singleShot(
                600,
                lambda: self._write_device_done(model, vendor, ver_label, ver_num, serial),
            )
        except Exception as e:
            self.btn_dev_write.setText("写入")
            self.btn_dev_write.setEnabled(True)
            QMessageBox.warning(self, "写入失败", f"写入异常：{e}")

    def _write_device_done(self, model, vendor, ver_label, ver_num, serial):
        """设备信息写入完成回调"""
        self.btn_dev_write.setText("写入")
        self.btn_dev_write.setEnabled(True)
        # 表计 ID（H/D）只读，写入成功后按序列号更新展示
        self.f_meter_id_h.setText(f"{serial:X}")
        self.f_meter_id_d.setText(str(serial))
        self._set_device_synced(True)
        QMessageBox.information(
            self, "写入成功",
            f"设备基本信息标识已写入设备：\n"
            f"  设备型号：{model}\n"
            f"  厂商代码：{vendor}\n"
            f"  版本标签：{ver_label}\n"
            f"  版本号：{ver_num}\n"
            f"  产品序列号：{serial}"
        )

    # ===== 读取 =====

    def _on_read(self):
        """从设备读取国网协议参数 → 回填表单"""
        # 模拟/真实串口读取：这里用 mock 数据回填
        if not serial_manager.is_connected:
            QMessageBox.warning(
                self, "读取失败",
                "串口未连接，无法读取参数。\n（演示模式将直接使用默认值）"
            )
            return

        # TODO: 真实协议解析后回填。下面用模拟值演示流程
        try:
            # 程序填充时屏蔽信号，避免误触发"未同步"
            self._set_fields(
                address="1",
                baud_index=2,    # 9600
                parity_index=0,  # 无校验
                reset_time=True,
            )
            self._set_synced(True)
            QMessageBox.information(self, "读取成功", "已从设备读取国网协议参数")
        except Exception as e:
            QMessageBox.warning(self, "读取失败", f"读取异常：{e}")

    def _set_fields(self, *, address: str, baud_index: int,
                    parity_index: int, reset_time: bool):
        """程序填充字段（屏蔽信号）"""
        widgets = [self.f_addr, self.f_datetime]
        combos = [self.f_baud, self.f_parity]
        for w in widgets:
            w.blockSignals(True)
        for c in combos:
            c.blockSignals(True)

        self.f_addr.setText(address)
        self.f_baud.setCurrentIndex(baud_index)
        self.f_parity.setCurrentIndex(parity_index)
        if reset_time:
            self._reset_datetime_to_now()

        for w in widgets:
            w.blockSignals(False)
        for c in combos:
            c.blockSignals(False)

    # ===== 写入 =====

    def _on_write(self):
        """把表单值写入设备"""
        addr_text = self.f_addr.text().strip()
        # 校验：通信地址 1-247
        try:
            addr = int(addr_text)
            if not (1 <= addr <= 247):
                raise ValueError
        except ValueError:
            QMessageBox.warning(
                self, "写入失败",
                "通信地址必须为 1 ~ 247 之间的整数"
            )
            return

        baud = self.f_baud.currentData()
        parity = self.f_parity.currentData()
        dt = self.f_datetime.dateTime().toString("yyyy-MM-dd HH:mm:ss")

        if not serial_manager.is_connected:
            QMessageBox.warning(
                self, "写入失败",
                "串口未连接，无法写入参数。\n（演示模式将只显示待写入的值）"
            )
            # 即使未连接，仍然展示参数让用户确认
            QMessageBox.information(
                self, "待写入参数（演示）",
                f"通信地址：{addr}\n"
                f"波特率：{baud}（{self.f_baud.currentText().split(':')[1]}）\n"
                f"奇偶校验位：{parity}（{self.f_parity.currentText().split(':')[1]}）\n"
                f"日期时间：{dt}"
            )
            return

        # TODO: 真实协议打包下发。下面仅模拟成功
        try:
            # 模拟写入延迟
            self.btn_write.setText("写入中...")
            self.btn_write.setEnabled(False)
            QTimer.singleShot(600, lambda: self._write_done(addr, baud, parity, dt))
        except Exception as e:
            self.btn_write.setText("写入")
            self.btn_write.setEnabled(True)
            QMessageBox.warning(self, "写入失败", f"写入异常：{e}")

    def _write_done(self, addr, baud, parity, dt):
        """写入完成回调"""
        self.btn_write.setText("写入")
        self.btn_write.setEnabled(True)
        self._set_synced(True)
        QMessageBox.information(
            self, "写入成功",
            f"国网协议参数已写入设备：\n"
            f"  通信地址：{addr}\n"
            f"  波特率：{baud}\n"
            f"  奇偶校验位：{parity}\n"
            f"  日期时间：{dt}"
        )

    # ===== 第三卡：传感器状态 自动采集 =====

    def _toggle_auto_sensor(self):
        """切换自动采集开关"""
        self._auto_sensor = not self._auto_sensor
        if self._auto_sensor:
            self.btn_auto_sensor.setProperty("variant", "primary")
            # 二次设置 style 让 QSS 立刻生效
            self.btn_auto_sensor.style().unpolish(self.btn_auto_sensor)
            self.btn_auto_sensor.style().polish(self.btn_auto_sensor)
            self.btn_auto_sensor.setText("停止采集")
            self.sensor_state_tag.update_state("采集中", "ok")
            self._sensor_timer.start()
            # 立刻触发一次采集
            self._on_sensor_tick()
        else:
            self.btn_auto_sensor.setProperty("variant", "secondary")
            self.btn_auto_sensor.style().unpolish(self.btn_auto_sensor)
            self.btn_auto_sensor.style().polish(self.btn_auto_sensor)
            self.btn_auto_sensor.setText("自动采集")
            self._sensor_timer.stop()
            self.sensor_state_tag.update_state("已停止", "warn")

    def _on_sensor_tick(self):
        """每轮采集：模拟读取 9 路传感器状态位"""
        import random
        if not serial_manager.is_connected:
            self.sensor_state_tag.update_state("未连接", "warn")
            return
        # 主状态：默认 ok（绿色 + "正常"），10% 概率 warn（红色 + "异常"）
        main_state = "warn" if random.random() < 0.1 else "ok"
        if main_state == "warn":
            self.sensor_main_dot.setStyleSheet(
                f"background: {theme.HEX['DANGER']}; border-radius: 7px; border: none;"
            )
            self.sensor_main_text.setText("异常")
            self.sensor_main_text.setStyleSheet(
                f"color: {theme.HEX['DANGER']}; font-size: {theme.FS_MD}pt; "
                f"font-weight: {theme.FW_BOLD};"
            )
        else:
            self.sensor_main_dot.setStyleSheet(
                f"background: {theme.HEX['OK']}; border-radius: 7px; border: none;"
            )
            self.sensor_main_text.setText("正常")
            self.sensor_main_text.setStyleSheet(
                f"color: {theme.HEX['OK']}; font-size: {theme.FS_MD}pt; "
                f"font-weight: {theme.FW_BOLD};"
            )
        # 9 个状态框：二态（绿/红），约 15% 异常
        for box in self._sensor_boxes:
            box.set_state("warn" if random.random() < 0.15 else "ok")

    # ===== 第四卡：实时数据 自动采集 =====

    def _toggle_auto_realtime(self):
        """切换实时数据自动采集开关"""
        self._auto_realtime = not self._auto_realtime
        if self._auto_realtime:
            self.btn_auto_realtime.setProperty("variant", "primary")
            self.btn_auto_realtime.style().unpolish(self.btn_auto_realtime)
            self.btn_auto_realtime.style().polish(self.btn_auto_realtime)
            self.btn_auto_realtime.setText("停止采集")
            self.realtime_state_tag.update_state("采集中", "ok")
            self._realtime_timer.start()
            self._on_realtime_tick()
        else:
            self.btn_auto_realtime.setProperty("variant", "secondary")
            self.btn_auto_realtime.style().unpolish(self.btn_auto_realtime)
            self.btn_auto_realtime.style().polish(self.btn_auto_realtime)
            self.btn_auto_realtime.setText("自动采集")
            self._realtime_timer.stop()
            self.realtime_state_tag.update_state("已停止", "warn")

    def _on_realtime_tick(self):
        """每轮采集：模拟读取 4 路实时数据"""
        import random
        if not serial_manager.is_connected:
            self.realtime_state_tag.update_state("未连接", "warn")
            for m in self._realtime_metrics.values():
                m.set_value(None, False)
            return
        # 模拟数值（演示用，按 SF6 密度监测典型范围）
        self._realtime_metrics["density"].set_value(
            round(40 + random.uniform(-2, 2), 3), True
        )
        self._realtime_metrics["temp"].set_value(
            round(20 + random.uniform(-5, 15), 1), True
        )
        self._realtime_metrics["pressure"].set_value(
            round(0.35 + random.uniform(-0.05, 0.05), 3), True
        )
        self._realtime_metrics["water"].set_value(
            round(80 + random.uniform(-20, 40), 2), True
        )

    # ===== 第五卡：阈值设置 读 / 写 =====

    def _set_threshold_synced(self, synced: bool):
        """切换阈值卡状态 tag"""
        if synced:
            self.threshold_state_tag.update_state("已同步", "ok")
        else:
            self.threshold_state_tag.update_state("未保存", "warn")

    def _on_threshold_changed(self, *_args):
        """任一阈值字段改动 → 标记未保存"""
        self._set_threshold_synced(False)

    def _on_read_thresholds(self):
        """从设备读取阈值 → 回填表单（演示用模拟值）"""
        if not serial_manager.is_connected:
            QMessageBox.warning(
                self, "读取失败",
                "串口未连接，无法读取阈值。\n（演示模式将直接使用默认值）"
            )
            return
        try:
            # 屏蔽信号，避免程序填充触发"未保存"
            edits = list(self._thr_fields.values())
            for e in edits:
                e.blockSignals(True)
            self._thr_fields["alarm"].setText("0.45")
            self._thr_fields["lock1"].setText("0.35")
            self._thr_fields["lock2"].setText("0.30")
            self._thr_fields["overpress"].setText("0.55")
            for e in edits:
                e.blockSignals(False)
            self._set_threshold_synced(True)
            QMessageBox.information(self, "读取成功", "已从设备读取阈值参数")
        except Exception as e:
            QMessageBox.warning(self, "读取失败", f"读取异常：{e}")

    def _on_write_thresholds(self):
        """把表单值写入设备"""
        # 收集 + 校验
        values: dict[str, str] = {}
        for name, edit in self._thr_fields.items():
            text = edit.text().strip()
            if not text:
                QMessageBox.warning(
                    self, "写入失败",
                    f"阈值不能为空：{THRESHOLD_FIELDS[[n for n, _ in THRESHOLD_FIELDS].index(name)][1]}"
                )
                return
            try:
                float(text)  # 校验为合法数字
            except ValueError:
                QMessageBox.warning(
                    self, "写入失败",
                    f"阈值必须为数字：{text}"
                )
                return
            values[name] = text

        if not serial_manager.is_connected:
            QMessageBox.warning(
                self, "写入失败",
                "串口未连接，无法写入阈值。\n（演示模式将只显示待写入的值）"
            )
            QMessageBox.information(
                self, "待写入阈值（演示）",
                f"报警节点阈值：{values['alarm']}\n"
                f"闭锁1阈值：{values['lock1']}\n"
                f"闭锁2阈值：{values['lock2']}\n"
                f"超压节点阈值：{values['overpress']}"
            )
            return

        try:
            self.btn_thr_write.setText("写入中...")
            self.btn_thr_write.setEnabled(False)
            QTimer.singleShot(600, lambda: self._write_thresholds_done(values))
        except Exception as e:
            self.btn_thr_write.setText("写入")
            self.btn_thr_write.setEnabled(True)
            QMessageBox.warning(self, "写入失败", f"写入异常：{e}")

    def _write_thresholds_done(self, values: dict[str, str]):
        """阈值写入完成回调"""
        self.btn_thr_write.setText("写入")
        self.btn_thr_write.setEnabled(True)
        self._set_threshold_synced(True)
        QMessageBox.information(
            self, "写入成功",
            f"阈值参数已写入设备：\n"
            f"  报警节点阈值：{values['alarm']}\n"
            f"  闭锁1阈值：{values['lock1']}\n"
            f"  闭锁2阈值：{values['lock2']}\n"
            f"  超压节点阈值：{values['overpress']}"
        )

    # ===== 生命周期 =====

    def hideEvent(self, event):
        """离开页面时停止所有定时器，避免后台跑空"""
        super().hideEvent(event)
        if self._sensor_timer.isActive():
            self._sensor_timer.stop()
        if self._realtime_timer.isActive():
            self._realtime_timer.stop()