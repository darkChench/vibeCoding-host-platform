"""
实时监控页

迁移自原型 js/pages/monitor.js。
布局：上卡实时点位（metric 卡网格，2 列）+ 下卡短周期趋势（QtCharts 多折线）。

数据来源：
  metric 点位与趋势曲线都来自 store.sample_params()（category="采样参数"），
  在参数配置页增删后自动跟随。
  数值通过后台 PollWorker 线程调用协议层 read_param 刷新（模拟回包，真实串口阶段替换 transport）。

曲线显隐：chip 点击切换 store.curve_visible[name]，曲线只画启用集。
颜色按采样参数在完整列表中的索引固定（PALETTE 循环），不随显隐变化。
"""
from collections import deque

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
from PySide6.QtCore import Qt, Signal, QPointF, QDateTime, QMargins
from PySide6.QtGui import QColor, QPainter, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QComboBox,
)
from PySide6.QtGui import QWheelEvent

from .. import theme
from ..store import store
from ..workers.poll_worker import PollWorker

# 曲线调色板（主色蓝/绿/橙/红/灰/深蓝循环），颜色固定不随显隐变化
PALETTE = ["#0b6fb3", "#11875d", "#b86b00", "#bf3a46", "#617083", "#07588e"]

# 趋势窗口固定点数上限（无论选多长时间范围，点数不超过此值，内存/渲染稳定）
TREND_POINTS = 360

# 时间范围档位：标签 → (总秒数, 采样间隔秒, X 轴时间格式)
# 点数 = 总秒数 / 间隔秒，约等于 TREND_POINTS
TIME_RANGES = [
    ("1 分钟",  60,     1,   "HH:mm:ss"),
    ("10 分钟", 600,    2,   "HH:mm:ss"),
    ("1 小时",  3600,   10,  "HH:mm:ss"),
    ("1 天",    86400,  240, "HH:mm"),
]


class NoWheelComboBox(QComboBox):
    """禁用鼠标滚轮修改的下拉框（防止误操作）"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class MetricCard(QFrame):
    """单个点位卡：显示名 + 数值(大) + 单位(小)"""

    def __init__(self, name: str, display: str, unit: str):
        super().__init__()
        self.setObjectName("metric")
        self._name = name
        self._unit = unit

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
        """刷新数值。value 为 float 或 None（失败显示 --）

        用 <font color> + <small> 标签（Qt 富文本子集），单位用 MUTED 色 + 小字。
        """
        muted = theme.HEX["MUTED"]
        if not ok or value is None:
            num = "--"
        else:
            num = f"{value}"
        self.value.setText(f'{num}<small><font color="{muted}"> {self._unit}</font></small>')


class CurveChip(QFrame):
    """曲线筛选 chip：圆点 + 显示名，点击切换显隐

    用 QFrame + 圆点 QLabel + 文本 QLabel 三件套，避免 QPushButton 富文本不可靠的问题。
    每个组件独立用 setStyleSheet 控制颜色，不依赖富文本渲染。
    """

    clicked = Signal(str)  # 参数名

    def __init__(self, name: str, display: str, color: str, visible: bool):
        super().__init__()
        self.setObjectName("curve-chip")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(26)
        self._name = name
        self._display = display
        self._color = color
        self._visible = visible

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(6)

        # 圆点：用固定尺寸 QLabel + border-radius 做正圆（比 Unicode ● 更精致可控）
        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)

        self._text = QLabel(display)
        self._text.setObjectName("chip-text")

        lay.addWidget(self._dot)
        lay.addWidget(self._text)
        self._apply_state()

    def _apply_state(self):
        """按 visible 切换圆点色、文字色、删除线（圆角/边框由全局 QSS 控制）"""
        dot_color = self._color if self._visible else "#aab6c4"
        text_color = theme.HEX["TEXT"] if self._visible else theme.HEX["MUTED"]
        # 圆点用背景色 + 正圆 border-radius
        self._dot.setStyleSheet(
            f"background: {dot_color}; border-radius: 4px; border: none;"
        )
        font = self._text.font()
        font.setStrikeOut(not self._visible)
        self._text.setFont(font)
        self._text.setStyleSheet(f"color: {text_color}; border: none; background: transparent;")
        self.setProperty("hidden", "true" if not self._visible else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def toggle(self):
        self._visible = not self._visible
        self._apply_state()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
            self.clicked.emit(self._name)
        super().mouseReleaseEvent(event)


class MonitorPage(QWidget):
    """实时监控页"""

    def __init__(self):
        super().__init__()
        self._worker: PollWorker | None = None
        self._metric_cards: dict[str, MetricCard] = {}
        self._chips: dict[str, CurveChip] = {}
        self._series: dict[str, QLineSeries] = {}
        self._trend: dict[str, deque] = {}
        self._container = QVBoxLayout(self)
        self._container.setContentsMargins(12, 12, 12, 12)
        self._container.setSpacing(10)
        self._content: QWidget | None = None
        # 当前时间范围：(总秒数, 采样间隔秒, X 轴格式)，默认 1 分钟
        self._time_span: int = 60
        self._sample_interval: int = 1
        self._time_format: str = "HH:mm:ss"
        self._build_content()

    # ===== 布局 =====

    def _build_content(self):
        """根据连接状态/参数表重建整页内容"""
        # 清空旧内容
        if self._content:
            self._content.setParent(None)
            self._content.deleteLater()
        self._metric_cards.clear()
        self._chips.clear()
        self._series.clear()
        self._trend.clear()

        connected = store.connection_state == "connected"
        params = store.sample_params()

        # 空态
        if not connected or not params:
            reason = "串口未连接" if not connected else "暂无采样参数（请在参数配置页新增 category=采样参数 的条目）"
            self._content = self._build_empty(reason, connected)
            self._container.addWidget(self._content)
            return

        # 正常态
        self._content = QWidget()
        lay = QVBoxLayout(self._content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(self._build_metric_card(params))
        lay.addWidget(self._build_chart_card(params), 1)  # 趋势卡弹性拉伸
        self._container.addWidget(self._content)

    def _build_metric_card(self, params: list[dict]) -> QFrame:
        """上卡：实时点位 metric 网格（2 列）"""
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # head
        head = QFrame()
        head.setObjectName("card-head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(10, 0, 10, 0)
        title = QLabel("实时点位")
        title.setObjectName("card-title")

        # 运行状态：胶囊样式（绿色圆点 + 文字），和曲线 chip 风格统一
        status = QFrame()
        status.setObjectName("status-chip")
        status.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        status.setFixedHeight(26)
        sl = QHBoxLayout(status)
        sl.setContentsMargins(10, 0, 10, 0)
        sl.setSpacing(6)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {theme.HEX['OK']}; border-radius: 4px; border: none;")
        stext = QLabel("运行")
        stext.setStyleSheet(f"color: {theme.HEX['OK']}; font-size: {theme.FS_SM}pt; font-weight: {theme.FW_BOLD}; border: none; background: transparent;")
        sl.addWidget(dot)
        sl.addWidget(stext)

        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(status, alignment=Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(head)

        # body：2 列网格
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for i, p in enumerate(params):
            row, col = divmod(i, 2)
            mc = MetricCard(p["name"], p.get("display", ""), p.get("unit", ""))
            grid.addWidget(mc, row, col)
            self._metric_cards[p["name"]] = mc
        cl.addWidget(body, 1)
        return card

    def _build_chart_card(self, params: list[dict]) -> QFrame:
        """下卡：短周期趋势（chip 行 + QtCharts）"""
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # head：标题 + 时间范围 + chip 行 + 暂停按钮
        head = QFrame()
        head.setObjectName("card-head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(10, 0, 10, 0)
        title = QLabel("短周期趋势")
        title.setObjectName("card-title")
        hl.addWidget(title)

        # 时间范围下拉（紧凑高度，和标题文字行高一致）
        self.range_combo = NoWheelComboBox()
        self.range_combo.addItems([r[0] for r in TIME_RANGES])
        self.range_combo.setStyleSheet(
            "QComboBox { min-height: 26px; padding: 0 6px; font-size: 10pt; }"
            "QComboBox::drop-down { width: 16px; }"
        )
        self.range_combo.currentIndexChanged.connect(self._on_time_range_changed)
        hl.addWidget(self.range_combo, alignment=Qt.AlignmentFlag.AlignVCenter)

        hl.addStretch()

        chip_row = QHBoxLayout()
        chip_row.setSpacing(5)
        for i, p in enumerate(params):
            color = PALETTE[i % len(PALETTE)]
            visible = store.get_curve_visible(p["name"])
            chip = CurveChip(p["name"], p.get("display", "") or p["name"], color, visible)
            chip.clicked.connect(lambda name=p["name"]: self._on_chip_clicked(name))
            chip_row.addWidget(chip)
            self._chips[p["name"]] = chip
        hl.addLayout(chip_row)

        # 暂停/继续按钮（默认暂停，用户点"开始采样"才启动轮询）
        self._paused = True
        self.btn_pause = QPushButton("开始采样")
        self.btn_pause.setObjectName("btn-pause")
        self.btn_pause.setProperty("variant", "secondary")
        self.btn_pause.setFixedHeight(26)
        self.btn_pause.setStyleSheet("QPushButton { min-height: 26px; padding: 0 10px; }")
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.clicked.connect(self._toggle_pause)
        hl.addWidget(self.btn_pause, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 清除按钮：清空所有曲线数据
        self.btn_clear = QPushButton("清除")
        self.btn_clear.setObjectName("btn-clear")
        self.btn_clear.setProperty("variant", "secondary")
        self.btn_clear.setFixedHeight(26)
        self.btn_clear.setStyleSheet("QPushButton { min-height: 26px; padding: 0 10px; }")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self._clear_chart)
        hl.addWidget(self.btn_clear, alignment=Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(head)

        # body：图表（弹性填充，内边距归零让绘图区最大化）
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        self._chart_view = self._build_chart(params)
        bl.addWidget(self._chart_view)
        cl.addWidget(body, 1)
        return card

    def _build_chart(self, params: list[dict]) -> QChartView:
        """构建 QtCharts 图表（所有 series 都创建，按 curve_visible 显隐）"""
        from PySide6.QtGui import QPen
        from PySide6.QtCore import Qt as QtConst

        self._chart = QChart()
        self._chart.legend().hide()
        # 四周边距全部归零，绘图区最大化
        self._chart.layout().setContentsMargins(0, 0, 0, 0)
        self._chart.setMargins(QMargins(0, 0, 0, 0))
        # 外层透明（融入卡片白底）
        self._chart.setBackgroundVisible(False)
        # 绘图区：浅蓝底（原型 .chart #fbfdff），无边框（NoPen 去掉灰线）
        self._chart.setPlotAreaBackgroundVisible(True)
        self._chart.setPlotAreaBackgroundBrush(QBrush(QColor("#fbfdff")))
        no_pen = QPen(QtConst.PenStyle.NoPen)
        self._chart.setPlotAreaBackgroundPen(no_pen)

        # 网格线统一用极淡色（比 LINE 更浅，不抢视线）
        grid = "#eef3f8"

        # X 轴：时间轴，范围和格式跟随当前时间范围档位
        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat(self._time_format)
        self._axis_x.setTickCount(6)
        self._axis_x.setTitleText("时间")
        now = QDateTime.currentDateTime()
        self._axis_x.setRange(now.addSecs(-self._time_span), now)
        self._axis_x.setGridLineColor(QColor(grid))
        self._axis_x.setLinePenColor(QColor(grid))
        self._axis_x.setLabelsColor(QColor(theme.HEX["MUTED"]))
        self._axis_x.setTitleBrush(QBrush(QColor(theme.HEX["MUTED"])))
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)

        # Y 轴：自动范围
        self._axis_y = QValueAxis()
        self._axis_y.setRange(0, 100)
        self._axis_y.setTickCount(5)
        self._axis_y.setGridLineColor(QColor(grid))
        self._axis_y.setLinePenColor(QColor(grid))
        self._axis_y.setLabelsColor(QColor(theme.HEX["MUTED"]))
        self._axis_y.setLabelsFont(self._axis_y.labelsFont())  # 默认字体
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)

        # 每个参数一条 series
        self._param_info: dict[str, dict] = {}  # name → 参数字典（供 Y 轴标题用）
        for i, p in enumerate(params):
            self._param_info[p["name"]] = p
            series = QLineSeries()
            color = PALETTE[i % len(PALETTE)]
            series.setColor(QColor(color))
            pen = series.pen()
            pen.setWidthF(1.6)
            series.setPen(pen)
            self._chart.addSeries(series)
            series.attachAxis(self._axis_x)
            series.attachAxis(self._axis_y)
            series.setVisible(store.get_curve_visible(p["name"]))
            self._series[p["name"]] = series
            self._trend[p["name"]] = deque(maxlen=TREND_POINTS)

        view = QChartView(self._chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setObjectName("chart-view")
        view.setFrameShape(QFrame.Shape.NoFrame)
        # QChartView 背景透明，露出卡片白底（避免灰色框包裹绘图区）
        view.setBackgroundBrush(QBrush(QColor("#ffffff")))
        view.setStyleSheet("background: transparent;")
        return view

    def _build_empty(self, reason: str, connected: bool) -> QWidget:
        """空态页（两卡都显示空态文案）"""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        tag_text = "无数据" if connected else "未连接"
        tag_variant = "warn"

        for title, icon in [("实时点位", "📊"), ("短周期趋势", "📈")]:
            card = QFrame()
            card.setObjectName("card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(0)
            head = QFrame()
            head.setObjectName("card-head")
            hl = QHBoxLayout(head)
            hl.setContentsMargins(10, 0, 10, 0)
            t = QLabel(title)
            t.setObjectName("card-title")
            tag = QLabel(tag_text)
            tag.setObjectName("tag")
            tag.setProperty("variant", tag_variant)
            tag.setFixedHeight(18)
            hl.addWidget(t)
            hl.addStretch()
            hl.addWidget(tag)
            cl.addWidget(head)
            body = QFrame()
            bl = QVBoxLayout(body)
            bl.setContentsMargins(10, 10, 10, 10)
            empty = QLabel(f'{icon}  {reason}')
            empty.setObjectName("empty-state")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setMinimumHeight(120)
            bl.addWidget(empty)
            cl.addWidget(body, 1)
            lay.addWidget(card)
        lay.addStretch()
        return w

    # ===== tick 处理 =====

    def _on_tick(self, values: dict):
        """每轮采样完成：刷新 metric + 追加曲线点（带时间戳）

        暂停时 metric 值仍刷新，但曲线冻结（不追加新点、不滚动 X 轴）。
        """
        now_ms = QDateTime.currentMSecsSinceEpoch()
        for name, info in values.items():
            card = self._metric_cards.get(name)
            if card:
                card.set_value(info["value"], info["ok"])

            # 暂停时跳过曲线更新（冻结当前画面）
            if self._paused:
                continue

            # 追加趋势点（时间戳 + 值）
            series = self._series.get(name)
            if series:
                v = info["value"] if info["ok"] else 0.0
                self._trend[name].append((now_ms, v))
                # 重建 series 点：X = 毫秒时间戳，Y = 值
                pts = [QPointF(float(ts), float(val)) for ts, val in self._trend[name]]
                if pts:
                    series.replace(pts)

        # 暂停时冻结 X 轴滚动和 Y 轴范围
        if self._paused:
            return

        # X 轴范围跟随最新数据滚动（窗口 = 当前时间范围）
        newest = QDateTime.fromMSecsSinceEpoch(now_ms)
        self._axis_x.setRange(newest.addSecs(-self._time_span), newest)
        # 更新 Y 轴范围（仅可见 series）
        self._update_y_axis()

    def _update_y_axis(self):
        """根据当前可见曲线的 min/max 调整 Y 轴范围（+10% 余量）。

        只显示 1 条曲线时，Y 轴标题显示该参数名称+单位；
        2 条及以上或多条/无可见时不显示标题。
        """
        visible_names = [n for n, s in self._series.items() if s.isVisible()]

        # Y 轴标题：仅 1 条可见曲线时显示"名称 (单位)"
        if len(visible_names) == 1:
            p = self._param_info.get(visible_names[0], {})
            display = p.get("display", "") or p.get("name", "")
            unit = p.get("unit", "")
            title = f"{display} ({unit})" if unit else display
            self._axis_y.setTitleText(title)
            self._axis_y.setTitleBrush(QBrush(QColor(theme.HEX["MUTED"])))
        else:
            self._axis_y.setTitleText("")

        lo, hi = None, None
        for name in visible_names:
            series = self._series[name]
            for pt in series.pointsVector():
                v = pt.y()
                lo = v if lo is None else min(lo, v)
                hi = v if hi is None else max(hi, v)
        if lo is None or hi is None or lo == hi:
            self._axis_y.setRange(0, 100)
            return
        span = hi - lo
        margin = span * 0.1 if span > 0 else 1
        self._axis_y.setRange(lo - margin, hi + margin)

    # ===== 暂停/继续 =====

    def _toggle_pause(self):
        """切换暂停状态：默认暂停，点"开始采样"启动轮询，再点"暂停"停止"""
        self._paused = not self._paused
        self.btn_pause.setText("暂停" if not self._paused else "开始采样")
        # 暂停时停止轮询线程，恢复时重新启动
        if self._paused:
            self._stop_worker()
        else:
            self._start_worker()

    def _clear_chart(self):
        """清空所有曲线数据（趋势 deque + series 点）"""
        for name in self._trend:
            self._trend[name].clear()
        for series in self._series.values():
            series.replace([])
        self._update_y_axis()

    # ===== 时间范围切换 =====

    def _on_time_range_changed(self, index: int):
        """切换时间范围档位：更新采样间隔/窗口/X 轴格式，清空旧数据并重启轮询"""
        _, span, interval, fmt = TIME_RANGES[index]
        self._time_span = span
        self._sample_interval = interval
        self._time_format = fmt
        # 更新 X 轴格式和范围
        self._axis_x.setFormat(fmt)
        now = QDateTime.currentDateTime()
        self._axis_x.setRange(now.addSecs(-span), now)
        # 清空趋势数据（不同档位间隔不同，旧数据不兼容）
        for name in self._trend:
            self._trend[name].clear()
        for series in self._series.values():
            series.replace([])
        # 重启轮询线程（用新采样间隔），仅在非暂停状态
        was_running = self._worker is not None and self._worker.isRunning()
        self._stop_worker()
        if (was_running or self.isVisible()) and not self._paused:
            self._start_worker()

    # ===== chip 交互 =====

    def _on_chip_clicked(self, name: str):
        """chip 点击：切换 store.curve_visible + series 显隐（chip 视觉自己处理）"""
        cur = store.get_curve_visible(name)
        store.curve_visible[name] = not cur
        series = self._series.get(name)
        if series:
            series.setVisible(not cur)
        self._update_y_axis()

    # ===== 生命周期 =====

    def showEvent(self, event):
        """页面可见时启动轮询（仅在非暂停状态）"""
        super().showEvent(event)
        if not self._paused:
            self._start_worker()

    def hideEvent(self, event):
        """页面隐藏时停止轮询"""
        super().hideEvent(event)
        self._stop_worker()

    def _start_worker(self):
        if store.connection_state != "connected":
            return
        params = store.sample_params()
        if not params:
            return
        if self._worker and self._worker.isRunning():
            self._worker.update_params(params)
            return
        self._worker = PollWorker(
            params, store.slave_id, interval_ms=self._sample_interval * 1000
        )
        self._worker.tick.connect(self._on_tick)
        self._worker.start()

    def _stop_worker(self):
        if self._worker:
            self._worker.stop()
            self._worker = None

    def refresh_params(self):
        """参数配置页增删采样参数后调用：重建整页 + 重启轮询（仅非暂停时）"""
        was_running = self._worker is not None and self._worker.isRunning()
        self._stop_worker()
        self._build_content()
        if (was_running or self.isVisible()) and not self._paused:
            self._start_worker()
