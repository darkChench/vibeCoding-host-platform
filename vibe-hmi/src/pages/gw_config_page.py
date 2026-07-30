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
from PySide6.QtCore import Qt, QDateTime, QDate, QTime, Signal, QTimer
from PySide6.QtGui import QWheelEvent

from .. import theme
from ..serial.serial_manager import serial_manager
from ..protocol.modbus_protocol import (
    build_gw_read_frame, parse_gw_read_response, GW_FC,
    build_gw_write_baud_frame, build_gw_write_parity_frame,
    build_gw_write_datetime_frame, build_gw_write_addr_frame,
    parse_gw_write_response,
)


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
        layout.addWidget(self._build_meter_addr_card())   # 表计通讯地址（modbus 通信地址源）
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

    # ===== 顶卡：表计通讯地址（modbus 通信地址源） =====

    def _build_meter_addr_card(self) -> QFrame:
        """顶卡：表计通讯地址

        单字段卡片：只显示「通信地址」（可编辑），不设读取/写入按钮。
        该值 = 设备当前地址，是下面「表计通信标识」卡片收发 modbus 帧时
        使用的**从机地址**。改址流程：本卡保持旧地址 → 下卡通信地址填新地址
        → 点写入（帧用旧地址下发）→ 设备确认成功后本卡自动同步为新地址。
        """
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # card-head：标题 + 状态 tag（无按钮）
        head = QFrame()
        head.setObjectName("card-head")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(10, 0, 10, 0)

        title = QLabel("表计通讯地址")
        title.setObjectName("card-title")
        head_layout.addWidget(title)

        head_layout.addStretch()

        # 状态 tag：未配置 / 已配置 / 校验失败
        from .params_page import StatusChip
        self.addr_state_tag = StatusChip("未配置", "warn")
        head_layout.addWidget(self.addr_state_tag, alignment=Qt.AlignmentFlag.AlignVCenter)

        card_layout.addWidget(head)

        # body：单字段（通信地址）
        body = QWidget()
        form = QGridLayout(body)
        form.setContentsMargins(14, 12, 14, 14)
        form.setVerticalSpacing(12)
        form.setHorizontalSpacing(12)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)

        # 通信地址（QLineEdit，1-247）
        self.f_meter_addr = NoWheelLineEdit()
        self.f_meter_addr.setPlaceholderText("1 ~ 247")
        self.f_meter_addr.setText("1")
        self.f_meter_addr.setMaxLength(3)
        self.f_meter_addr.textChanged.connect(self._on_meter_addr_changed)

        form.addWidget(self._field("通信地址", self.f_meter_addr), 0, 0)

        card_layout.addWidget(body)
        return card

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

        # 字段 1：通信地址（目标地址 / 待写入地址）
        # 与顶卡「表计通讯地址」是两个独立的值：
        #   顶卡 = 设备当前地址（发送 modbus 帧时用的从机地址）
        #   本字段 = 想让设备变成的地址（写入时下发的新地址）
        # 读取后两者一致；改地址时只改本字段，写入成功后顶卡才同步成新值。
        self.f_comm_addr = NoWheelLineEdit()
        self.f_comm_addr.setPlaceholderText("1 ~ 247")
        self.f_comm_addr.setText("1")
        self.f_comm_addr.setMaxLength(3)
        self.f_comm_addr.textChanged.connect(self._on_form_changed)

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

        # 两列布局：通信地址 / 波特率 —— 奇偶校验位 / 日期时间
        form.addWidget(self._field("通信地址", self.f_comm_addr), 0, 0)
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

        # 字段 5：产品序列号（文本输入框）
        self.f_serial = NoWheelLineEdit()
        self.f_serial.setText(str(SERIAL_DEFAULT))
        self.f_serial.setPlaceholderText(f"{SERIAL_MIN}~{SERIAL_MAX}")
        self.f_serial.textChanged.connect(self._on_device_form_changed)

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

    # ===== 顶卡：表计通讯地址 校验回调 =====

    @staticmethod
    def _parse_addr(text: str):
        """把地址文本解析成 1~247 的整数；非法返回 None"""
        try:
            addr = int(text.strip())
        except ValueError:
            return None
        return addr if 1 <= addr <= 247 else None

    def _sync_meter_addr(self, addr: int):
        """把顶卡「表计通讯地址」同步成设备的当前地址

        仅在读取成功 / 写入成功之后调用：写入用的是旧地址，
        设备确认改址成功后，顶卡（从机地址源）才跟着变成新地址。
        """
        self.f_meter_addr.setText(str(addr))  # textChanged 会刷新状态 tag

    def _on_meter_addr_changed(self, *_args):
        """通信地址变更 → 校验 + 切换状态 tag"""
        text = self.f_meter_addr.text().strip()
        if not text:
            self.addr_state_tag.update_state("未配置", "warn")
            return
        try:
            addr = int(text)
        except ValueError:
            self.addr_state_tag.update_state("校验失败", "warn")
            return
        if 1 <= addr <= 247:
            self.addr_state_tag.update_state("已配置", "ok")
        else:
            self.addr_state_tag.update_state("校验失败", "warn")

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
        self.f_serial.setText(str(max(SERIAL_MIN, min(SERIAL_MAX, serial))))
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
        try:
            serial = int(self.f_serial.text().strip())
        except ValueError:
            QMessageBox.warning(self, "写入失败", "产品序列号必须是数字")
            return

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
        """从设备读取国网协议参数 → 回填表单

        modbus 从机地址 = 顶卡「表计通讯地址」（设备当前地址）。
        读回来的通信地址填进本卡的「通信地址」字段，读取后两处一致。

        协议（FC=0x66，非标准 Modbus）：
          请求：<slave> 66 03 01 20 00 <CRC_LO CRC_HI>
          响应：<slave> 66 0F 81 20 00 41 0A
                <addr> <baud> <parity> <year_LO year_HI>
                <month> <day> <hour> <minute> <second>
                <CRC_LO CRC_HI>
        """
        if not serial_manager.is_connected:
            QMessageBox.warning(
                self, "读取失败",
                "串口未连接，无法读取参数。\n（演示模式将直接使用默认值）"
            )
            return

        # modbus 从机地址取自顶卡「表计通讯地址」
        slave = self._parse_addr(self.f_meter_addr.text())
        if slave is None:
            QMessageBox.warning(
                self, "读取失败",
                "顶部「表计通讯地址」必须为 1 ~ 247 之间的整数"
            )
            return

        # 构建请求帧（<slave> 66 03 01 20 00 + CRC）
        request = build_gw_read_frame(slave)
        hex_req = " ".join(f"{b:02X}" for b in request)

        try:
            # 真实模式由 serial_manager 走串口；模拟模式也会生成响应帧
            resp_bytes = serial_manager.transact(bytes(request))
            if not resp_bytes:
                QMessageBox.warning(
                    self, "读取失败",
                    "设备无响应（超时），请检查串口连接和从机地址。"
                )
                return

            parsed = parse_gw_read_response(list(resp_bytes))
            if parsed is None:
                hex_resp = " ".join(f"{b:02X}" for b in resp_bytes)
                QMessageBox.warning(
                    self, "读取失败",
                    f"响应帧解析失败：\n{hex_resp}\n\n"
                    f"（期望：FC=0x{GW_FC:02X} + 至少 20 字节 + CRC 通过）"
                )
                return

            # 按解析结果回填表单
            self._set_fields(
                addr=parsed["addr"],
                baud_code=parsed["baud_code"],
                parity_code=parsed["parity_code"],
                datetime_tuple=(
                    parsed["year"], parsed["month"], parsed["day"],
                    parsed["hour"], parsed["minute"], parsed["second"],
                ),
            )
            # 读回来的地址即设备当前地址 → 同步顶卡
            self._sync_meter_addr(parsed["addr"])
            self._set_synced(True)

            hex_resp = " ".join(f"{b:02X}" for b in resp_bytes)
            QMessageBox.information(
                self, "读取成功",
                f"已从设备（从机地址 {slave}）读取国网协议参数\n\n"
                f"请求：{hex_req}\n"
                f"响应：{hex_resp}"
            )
        except Exception as e:
            QMessageBox.warning(self, "读取失败", f"读取异常：{e}")

    def _set_fields(self, *, addr: int, baud_code: int = None,
                    parity_code: int = None, reset_time: bool = False,
                    datetime_tuple: tuple = None):
        """程序填充字段（屏蔽信号）

        baud_code / parity_code: 设备返回的代码（baud: 0=2400 1=4800 2=9600 3=19200；
        parity: 0=无 1=奇 2=偶），按 userData 在 combo 中查找索引。
        datetime_tuple: (year, month, day, hour, minute, second)，优先级高于 reset_time。
        """
        widgets = [self.f_datetime, self.f_comm_addr]
        combos = [self.f_baud, self.f_parity]
        for w in widgets:
            w.blockSignals(True)
        for c in combos:
            c.blockSignals(True)

        self.f_comm_addr.setText(str(addr))

        if baud_code is not None:
            idx = self.f_baud.findData(baud_code)
            if idx >= 0:
                self.f_baud.setCurrentIndex(idx)
        if parity_code is not None:
            idx = self.f_parity.findData(parity_code)
            if idx >= 0:
                self.f_parity.setCurrentIndex(idx)

        if datetime_tuple is not None:
            year, month, day, hour, minute, second = datetime_tuple
            try:
                self.f_datetime.setDateTime(
                    QDateTime(QDate(year, month, day), QTime(hour, minute, second))
                )
            except Exception:
                # 设备返回的日期/时间字段非法时回退为当前时间
                self._reset_datetime_to_now()
        elif reset_time:
            self._reset_datetime_to_now()

        for w in widgets:
            w.blockSignals(False)
        for c in combos:
            c.blockSignals(False)

    # ===== 写入 =====

    # 写入步骤的顺序：波特率 → 奇偶校验位 → 日期时间 → 通信地址
    # 通信地址必须最后写：前 3 步用旧地址，地址改了之后顶卡从机地址才同步成新值。
    _WRITE_STEPS = ("baud", "parity", "datetime", "addr")
    _STEP_LABELS = {
        "baud":     "波特率",
        "parity":   "奇偶校验位",
        "datetime": "日期时间",
        "addr":     "通信地址",
    }

    def _on_write(self):
        """把表单值写入设备

        关键：帧里的从机地址用顶卡「表计通讯地址」（设备当前地址），
        下发的新通信地址用本卡的「通信地址」字段。
        例：设备现在是 1，想改成 20 → 顶卡填 1、本卡填 20，
        发出的帧从机地址是 01，设备改址成功后顶卡才自动变成 20。

        写入流程按国网协议规范分 4 步串行下发（每步等设备回包再下一步）：
          1) 波特率       <slave> 66 06 02 20 02 20 01 <baud_code>  CRC
          2) 奇偶校验位   <slave> 66 06 02 20 03 20 01 <parity_code> CRC
          3) 日期时间     <slave> 66 0C 02 20 04 40 07 <年LE 月 日 时 分 秒>  CRC
          4) 通信地址     <slave> 66 06 02 20 01 20 01 <addr>  CRC
        全部成功后顶卡「表计通讯地址」同步成写入的新地址。
        """
        # 1) 从机地址：顶卡「表计通讯地址」= 设备当前地址
        slave = self._parse_addr(self.f_meter_addr.text())
        if slave is None:
            QMessageBox.warning(
                self, "写入失败",
                "顶部「表计通讯地址」必须为 1 ~ 247 之间的整数\n"
                "（该值是发送 modbus 帧时使用的从机地址，需与设备当前地址一致）"
            )
            return

        # 2) 待写入的新通信地址：本卡「通信地址」
        new_addr = self._parse_addr(self.f_comm_addr.text())
        if new_addr is None:
            QMessageBox.warning(
                self, "写入失败",
                "「表计通信标识」中的通信地址必须为 1 ~ 247 之间的整数"
            )
            return

        baud = self.f_baud.currentData()
        parity = self.f_parity.currentData()
        qdt = self.f_datetime.dateTime()
        dt_str = qdt.toString("yyyy-MM-dd HH:mm:ss")

        # 收集 datetime 6 个分量
        year = qdt.date().year()
        month = qdt.date().month()
        day = qdt.date().day()
        hour = qdt.time().hour()
        minute = qdt.time().minute()
        second = qdt.time().second()

        if not serial_manager.is_connected:
            QMessageBox.warning(
                self, "写入失败",
                "串口未连接，无法写入参数。\n（演示模式将只显示待写入的值）"
            )
            # 即使未连接，仍然展示参数让用户确认
            QMessageBox.information(
                self, "待写入参数（演示）",
                f"从机地址（当前）：{slave}\n"
                f"通信地址（待写入）：{new_addr}\n"
                f"波特率：{baud}（{self.f_baud.currentText().split(':')[1]}）\n"
                f"奇偶校验位：{parity}（{self.f_parity.currentText().split(':')[1]}）\n"
                f"日期时间：{dt_str}"
            )
            return

        # 把所有参数暂存到 self，下一步状态机按顺序取用
        self._write_slave = slave
        self._write_new_addr = new_addr
        self._write_baud = baud
        self._write_parity = parity
        self._write_dt_str = dt_str
        self._write_year = year
        self._write_month = month
        self._write_day = day
        self._write_hour = hour
        self._write_minute = minute
        self._write_second = second
        self._write_step_index = 0
        self._write_results: list[dict] = []  # 每步的请求/响应回执
        self._write_busy = True

        self.btn_write.setText("写入中...")
        self.btn_write.setEnabled(False)
        # 启动分步状态机
        self._do_write_step()

    def _do_write_step(self):
        """执行当前步骤并自增：波特率→校验→时间→地址，全部成功后 _write_all_done。"""
        if not self._write_busy:
            return
        idx = self._write_step_index
        if idx >= len(self._WRITE_STEPS):
            self._write_all_done()
            return
        step = self._WRITE_STEPS[idx]

        try:
            if step == "baud":
                frame = build_gw_write_baud_frame(self._write_slave, self._write_baud)
            elif step == "parity":
                frame = build_gw_write_parity_frame(self._write_slave, self._write_parity)
            elif step == "datetime":
                frame = build_gw_write_datetime_frame(
                    self._write_slave,
                    self._write_year, self._write_month, self._write_day,
                    self._write_hour, self._write_minute, self._write_second,
                )
            elif step == "addr":
                frame = build_gw_write_addr_frame(self._write_slave, self._write_new_addr)
            else:
                raise ValueError(f"未知写入步骤：{step}")
        except ValueError as e:
            self._write_abort(f"参数非法：{e}", step, None, None)
            return

        # 发送并等待响应（transact 同步阻塞：模拟模式 50~100ms，真实模式最多 ~380ms）
        try:
            resp_bytes = serial_manager.transact(bytes(frame))
        except Exception as e:
            self._write_abort(f"串口异常：{e}", step, frame, None)
            return

        if not resp_bytes:
            self._write_abort("设备无响应（超时）", step, frame, None)
            return

        resp = list(resp_bytes)
        parsed = parse_gw_write_response(resp, frame)
        if parsed is None:
            hex_resp = " ".join(f"{b:02X}" for b in resp)
            self._write_abort(
                f"回包校验失败（FC/CRC 不通过）：\n{hex_resp}",
                step, frame, resp,
            )
            return

        # 该步成功，记录回执
        self._write_results.append({
            "step": step,
            "label": self._STEP_LABELS[step],
            "frame": frame,
            "resp": resp,
        })

        # 下一步（让 UI 有机会刷新）
        self._write_step_index += 1
        QTimer.singleShot(50, self._do_write_step)

    def _write_abort(self, reason: str, step: str,
                     frame: list[int] | None, resp: list[int] | None):
        """某一步失败：终止状态机，恢复按钮，弹错误框"""
        self._write_busy = False
        self.btn_write.setText("写入")
        self.btn_write.setEnabled(True)
        self._set_synced(False)

        lines = [f"第 {self._write_step_index + 1} 步「{self._STEP_LABELS[step]}」失败：{reason}"]
        if frame is not None:
            lines.append("请求：" + " ".join(f"{b:02X}" for b in frame))
        if resp is not None:
            lines.append("回包：" + " ".join(f"{b:02X}" for b in resp))
        lines.append(f"已完成 {len(self._write_results)} / {len(self._WRITE_STEPS)} 步，"
                     f"后续步骤未执行。")
        QMessageBox.warning(self, "写入失败", "\n".join(lines))

    def _write_all_done(self):
        """4 步全部成功：恢复按钮、同步顶卡、汇总展示"""
        self._write_busy = False
        self.btn_write.setText("写入")
        self.btn_write.setEnabled(True)

        slave = self._write_slave
        new_addr = self._write_new_addr
        baud = self._write_baud
        parity = self._write_parity
        dt_str = self._write_dt_str

        # 改址成功后，后续通信必须用新地址 → 同步顶卡
        self._sync_meter_addr(new_addr)
        self._set_synced(True)

        # 汇总 4 步的请求/响应（便于现场排错）
        step_lines = []
        for r in self._write_results:
            req_hex = " ".join(f"{b:02X}" for b in r["frame"])
            resp_hex = " ".join(f"{b:02X}" for b in r["resp"])
            step_lines.append(f"  [{r['label']}]")
            step_lines.append(f"    请求：{req_hex}")
            step_lines.append(f"    响应：{resp_hex}")

        addr_note = (
            f"  通信地址：{slave} → {new_addr}（顶部表计通讯地址已同步）\n"
            if new_addr != slave else
            f"  通信地址：{new_addr}（未变）\n"
        )
        QMessageBox.information(
            self, "写入成功",
            f"国网协议参数已分 4 步写入设备：\n"
            f"  从机地址（发送时）：{slave}\n"
            + addr_note +
            f"  波特率：{baud}\n"
            f"  奇偶校验位：{parity}\n"
            f"  日期时间：{dt_str}\n"
            f"\n报文流水：\n" + "\n".join(step_lines)
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