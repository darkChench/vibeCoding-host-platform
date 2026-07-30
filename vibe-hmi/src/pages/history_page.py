"""
历史数据页

迁移自原型 js/pages/history.js。
左右两列：卡片A 查询条件（form-grid + 按钮）+ 卡片B 趋势曲线（QtCharts）。
数据来源：监控页采样写入 SQLite（history_db）。
"""
import csv
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDateTimeEdit, QMessageBox, QFileDialog,
    QSizePolicy, QComboBox, QGridLayout,
)
from PySide6.QtCore import Qt, QDateTime, QEvent, QModelIndex, QAbstractItemModel, QMargins
from PySide6.QtGui import QColor, QPainter, QWheelEvent, QBrush

from .. import theme
from ..store import store
from .. import history_db

PALETTE = ["#0b6fb3", "#11875d", "#b86b00", "#bf3a46", "#617083", "#07588e"]


class NoWheelComboBox(QComboBox):
    """禁用鼠标滚轮的下拉框"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class CheckableComboBox(QComboBox):
    """多选下拉框：第一项为"全选/取消全选"，点击选项切换勾选，不关闭弹层。
    触发器显示已选汇总（如"温度、压力"），全不选时显示 placeholder。

    关键：重写 hidePopup，判断鼠标是否点在下拉项上——
    若是则切换该项勾选且不关闭弹层；否则（点空白/外部）才关闭。
    QComboBox 默认点击 item 会选中并关闭，必须拦截此行为才能多选。
    第一项"全选/取消全选"为控制项，不参与业务数据（get_selected 排除它）。
    """
    # 第一项固定文案，作为全选切换控制项
    SELECT_ALL_TEXT = "全选/取消全选"

    def __init__(self, placeholder: str = "请选择"):
        super().__init__()
        self._placeholder = placeholder
        self.setEditable(True)
        self.setEditText(placeholder)
        # 记录是否正在通过点击 item 触发隐藏（用于区分"点 item"和"点外部"）
        self._skip_hide = False

    def add_items(self, items: list[str]):
        """添加选项（默认全选）。

        第一项插入"全选/取消全选"控制项，其后为实际选项。
        """
        # 先插入全选控制项
        self.addItem(self.SELECT_ALL_TEXT)
        head = self.model().item(0, 0)
        head.setCheckState(Qt.CheckState.Checked)  # 默认全选 → 控制项打勾
        head.setFlags(head.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        # 插入实际选项（默认全选）
        for text in items:
            self.addItem(text)
            i = self.count() - 1
            item = self.model().item(i, 0)
            item.setCheckState(Qt.CheckState.Checked)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self._update_text()

    def get_selected(self) -> list[str]:
        """返回已选的业务项文本列表（排除第一项全选控制项）"""
        result = []
        for i in range(self.count()):
            if i == 0:  # 跳过全选控制项
                continue
            item = self.model().item(i, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                result.append(item.text())
        return result

    def _all_business_selected(self) -> bool:
        """判断所有业务项是否全部选中（不含全选控制项）"""
        for i in range(1, self.count()):
            item = self.model().item(i, 0)
            if not item or item.checkState() != Qt.CheckState.Checked:
                return False
        return True

    def _sync_select_all_state(self):
        """根据业务项选中状态，同步全选控制项的勾选（全选则打勾，否则取消）"""
        head = self.model().item(0, 0)
        if head:
            head.setCheckState(
                Qt.CheckState.Checked if self._all_business_selected() else Qt.CheckState.Unchecked
            )

    def _toggle_select_all(self):
        """点击全选控制项：若当前未全选则全选，否则全部取消"""
        target = (
            Qt.CheckState.Checked
            if not self._all_business_selected()
            else Qt.CheckState.Unchecked
        )
        for i in range(1, self.count()):
            item = self.model().item(i, 0)
            if item:
                item.setCheckState(target)
        # 同步全选控制项显示
        head = self.model().item(0, 0)
        if head:
            head.setCheckState(target)
        self._update_text()

    def _update_text(self):
        """更新显示文本（汇总，排除全选控制项；全选时显示"全部"避免拥挤）"""
        selected = self.get_selected()
        total = self.count() - 1  # 业务项总数
        if not selected:
            self.setEditText(self._placeholder)
        elif len(selected) == total and total > 3:
            # 选中全部且数量较多时，简洁显示"全部(N项)"
            self.setEditText(f"全部({total}项)")
        else:
            self.setEditText("、".join(selected))

    def showPopup(self):
        """弹出"""
        super().showPopup()

    def hidePopup(self):
        """关闭弹层：点 item 时切换勾选不关闭，点外部才关闭。

        通过鼠标全局坐标判断是否落在 popup 的 listview 范围内。
        点击第一项"全选/取消全选"时，联动设置所有业务项。
        """
        # 取下拉弹出的 listview（QComboBox 内部 view）
        view = self.view()
        if view is not None and view.isVisible():
            from PySide6.QtGui import QCursor
            # view 在全局坐标下的矩形
            view_global = view.viewport().mapToGlobal(view.viewport().rect().topLeft())
            from PySide6.QtCore import QRect
            view_rect = QRect(view_global, view.viewport().size())
            cursor_pos = QCursor.pos()
            # 鼠标在下拉项区域内 → 切换当前索引项的勾选，不关闭
            if view_rect.contains(cursor_pos):
                index = view.currentIndex()
                if index.isValid():
                    item = self.model().item(index.row(), 0)
                    if item and (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                        # 第一项：全选/取消全选联动
                        if index.row() == 0:
                            self._toggle_select_all()
                        else:
                            new_state = (
                                Qt.CheckState.Unchecked
                                if item.checkState() == Qt.CheckState.Checked
                                else Qt.CheckState.Checked
                            )
                            item.setCheckState(new_state)
                            self._sync_select_all_state()  # 同步全选控制项显示
                            self._update_text()
                # 阻止关闭
                return
        # 点外部 → 正常关闭并刷新文本
        super().hidePopup()
        self._update_text()


class HistoryPage(QWidget):
    """历史数据页"""

    def __init__(self):
        super().__init__()
        self._chart = None
        self._axis_x = None
        self._axis_y = None
        self._last_rows: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 上下显示：查询条件（上）+ 趋势曲线（下），参考实时监控页
        layout.addWidget(self._build_query_card())
        layout.addWidget(self._build_chart_card(), 1)

    # ===== 卡片A：查询条件 =====

    def _build_query_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # card-head
        head = QFrame()
        head.setObjectName("card-head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(10, 0, 10, 0)
        title = QLabel("查询条件")
        title.setObjectName("card-title")
        tag = QLabel("CSV")
        tag.setObjectName("tag")
        tag.setFixedHeight(18)
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(tag, alignment=Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(head)

        # card-body: form-grid 2 列（原型 .form-grid grid-template-columns: repeat(2, 1fr)）
        from PySide6.QtWidgets import QGridLayout
        body = QWidget()
        form = QVBoxLayout(body)
        form.setContentsMargins(14, 14, 14, 14)
        form.setSpacing(12)

        def field(label_text: str, widget) -> QWidget:
            f = QWidget()
            lay = QVBoxLayout(f)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(4)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {theme.HEX['MUTED']}; font-size: {theme.FS_SM}pt; font-weight: {theme.FW_BOLD};")
            lay.addWidget(lbl)
            lay.addWidget(widget)
            return f

        # 第一行：时间范围快捷按钮
        range_row = QHBoxLayout()
        range_row.setSpacing(6)
        range_lbl = QLabel("时间范围")
        range_lbl.setStyleSheet(f"color: {theme.HEX['MUTED']}; font-size: {theme.FS_SM}pt; font-weight: {theme.FW_BOLD}; padding-top: 3px;")
        range_lbl.setFixedHeight(28)  # 与按钮同高
        # 文字在 28px 框内垂直居中（QLabel 默认顶部对齐，会显得偏上）
        range_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        range_row.addWidget(range_lbl)

        self._range_buttons: dict[str, QPushButton] = {}
        self._current_range = "近1小时"
        for label, secs in [("近1小时", 3600), ("近6小时", 21600), ("近24小时", 86400), ("近7天", 604800)]:
            btn = QPushButton(label)
            btn.setProperty("variant", "secondary")
            btn.setFixedHeight(28)
            btn.setCheckable(True)
            btn.setChecked(label == self._current_range)
            btn.clicked.connect(lambda checked=False, l=label, s=secs: self._on_range_clicked(l, s))
            self._range_buttons[label] = btn
            range_row.addWidget(btn)

        # 自定义按钮
        self.btn_custom = QPushButton("自定义")
        self.btn_custom.setProperty("variant", "secondary")
        self.btn_custom.setFixedHeight(28)
        self.btn_custom.setCheckable(True)
        self.btn_custom.clicked.connect(self._on_custom_clicked)
        range_row.addWidget(self.btn_custom)
        range_row.addStretch()
        form.addLayout(range_row)

        # 自定义时间选择器（默认隐藏，点"自定义"才显示）
        self.custom_widget = QWidget()
        self.custom_widget.setVisible(False)
        custom_row = QHBoxLayout(self.custom_widget)
        custom_row.setContentsMargins(0, 0, 0, 0)
        custom_row.setSpacing(10)

        self.dt_start = QDateTimeEdit()
        self.dt_start.setDateTime(QDateTime.currentDateTime().addSecs(-3600))
        self.dt_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_start.setCalendarPopup(True)
        self.dt_end = QDateTimeEdit()
        self.dt_end.setDateTime(QDateTime.currentDateTime())
        self.dt_end.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_end.setCalendarPopup(True)

        custom_row.addWidget(QLabel("从"))
        custom_row.addWidget(self.dt_start)
        custom_row.addWidget(QLabel("到"))
        custom_row.addWidget(self.dt_end)
        custom_row.addStretch()
        form.addWidget(self.custom_widget)

        # 第二行：采样点位 + 导出格式
        fields_row = QHBoxLayout()
        fields_row.setSpacing(12)

        sample = store.sample_params()
        self.combo_params = CheckableComboBox("请选择点位")
        if sample:
            self.combo_params.add_items([p.get("display", "") or p["name"] for p in sample])
        else:
            self.combo_params.addItem("暂无采样参数")
            self.combo_params.setEnabled(False)

        self.combo_format = NoWheelComboBox()
        self.combo_format.addItems(["CSV"])
        self.combo_format.setStyleSheet("QComboBox { min-height: 28px; padding: 0 6px; }")

        fields_row.addWidget(field("采样点位", self.combo_params), 1)
        fields_row.addWidget(field("导出格式", self.combo_format))
        form.addLayout(fields_row)

        # 按钮行

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_query = QPushButton("查询")
        self.btn_query.clicked.connect(self._query)
        self.btn_export = QPushButton("导出")
        self.btn_export.setProperty("variant", "secondary")
        self.btn_export.clicked.connect(self._export)
        btn_row.addWidget(self.btn_query)
        btn_row.addWidget(self.btn_export)
        btn_row.addStretch()
        form.addLayout(btn_row)

        cl.addWidget(body)
        return card

    # ===== 卡片B：趋势曲线 =====

    def _build_chart_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # card-head
        head = QFrame()
        head.setObjectName("card-head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(10, 0, 10, 0)
        title = QLabel("趋势曲线")
        title.setObjectName("card-title")
        self.count_tag = QLabel("统计")
        self.count_tag.setObjectName("tag")
        self.count_tag.setFixedHeight(18)
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(self.count_tag, alignment=Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(head)

        # card-body（内边距归零，让绘图区最大化，与实时监控页一致）
        body = QWidget()
        body.setObjectName("card-body")
        body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)  # 让 QSS 背景生效
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)

        # 空态提示
        self.empty_label = QLabel('📈  请点击"查询"加载数据')
        self.empty_label.setObjectName("empty-state")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setMinimumHeight(200)
        bl.addWidget(self.empty_label)

        # QtCharts 容器（初始隐藏，查询后显示）
        self.chart_container = QWidget()
        self.chart_container.setObjectName("card-body")
        self.chart_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.chart_container.setVisible(False)
        chart_layout = QVBoxLayout(self.chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        self._chart_view = None  # 延迟创建
        bl.addWidget(self.chart_container)

        cl.addWidget(body, 1)
        return card

    # ===== 查询逻辑 =====

    def _get_selected_param_names(self) -> list[str]:
        """获取多选下拉中选中的参数名（通过显示名反查 name）"""
        selected_displays = self.combo_params.get_selected()
        name_map = {p.get("display", "") or p["name"]: p["name"] for p in store.sample_params()}
        return [name_map[d] for d in selected_displays if d in name_map]

    def _on_range_clicked(self, label: str, secs: int):
        """快捷时间范围按钮：选中后取消其他按钮，隐藏自定义选择器"""
        self._current_range = label
        for l, btn in self._range_buttons.items():
            btn.setChecked(l == label)
        self.btn_custom.setChecked(False)
        self.custom_widget.setVisible(False)
        # 更新时间范围
        self._range_secs = secs

    def _on_custom_clicked(self):
        """自定义按钮：展开日期选择器，取消快捷按钮选中"""
        checked = self.btn_custom.isChecked()
        self.custom_widget.setVisible(checked)
        if checked:
            for btn in self._range_buttons.values():
                btn.setChecked(False)
            self._current_range = "自定义"

    def _get_time_range(self) -> tuple[str, str]:
        """获取当前选择的开始/结束时间"""
        if self.btn_custom.isChecked():
            start = self.dt_start.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            end = self.dt_end.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        else:
            end = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            secs = getattr(self, "_range_secs", 3600)
            start = QDateTime.currentDateTime().addSecs(-secs).toString("yyyy-MM-dd HH:mm:ss")
        return start, end

    def _query(self):
        """查询历史数据 → 渲染趋势曲线"""
        param_names = self._get_selected_param_names()
        if not param_names:
            QMessageBox.warning(self, "查询", "请至少选择一个采样点位")
            return

        start, end = self._get_time_range()
        if start >= end:
            QMessageBox.warning(self, "查询", "开始时间必须早于结束时间")
            return

        # loading
        self.btn_query.setText("查询中...")
        self.btn_query.setEnabled(False)

        # 查询 SQLite
        rows = history_db.query(
            device_id=store.current_device_id,
            param_names=param_names,
            start_time=start,
            end_time=end,
        )
        self._last_rows = rows
        self.count_tag.setText(f"{len(rows)} 条")

        # 恢复按钮
        self.btn_query.setText("查询")
        self.btn_query.setEnabled(True)

        if not rows:
            self.empty_label.setText("📈  无符合条件的数据")
            self.empty_label.setVisible(True)
            self.chart_container.setVisible(False)
            return

        # 渲染趋势曲线
        self._render_chart(rows, param_names)

    def _render_chart(self, rows: list[dict], param_names: list[str]):
        """用 QtCharts 渲染历史趋势曲线"""
        from PySide6.QtCharts import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis

        # 清空旧的 chart
        if self._chart_view:
            self.chart_container.layout().removeWidget(self._chart_view)
            self._chart_view.deleteLater()
        self._chart_view = None

        # 隐藏空态，显示图表
        self.empty_label.setVisible(False)
        self.chart_container.setVisible(True)

        # 创建图表
        self._chart = QChart()
        self._chart.legend().hide()
        # 四周边距全部归零，绘图区最大化（与实时监控页一致）
        self._chart.layout().setContentsMargins(0, 0, 0, 0)
        self._chart.setMargins(QMargins(0, 0, 0, 0))
        # 外层透明（融入卡片白底）
        self._chart.setBackgroundVisible(False)
        # 绘图区：浅蓝底（原型 .chart #fbfdff），无边框（NoPen 去掉灰线）
        self._chart.setPlotAreaBackgroundVisible(True)
        self._chart.setPlotAreaBackgroundBrush(QBrush(QColor("#fbfdff")))
        from PySide6.QtGui import QPen
        self._chart.setPlotAreaBackgroundPen(QPen(Qt.PenStyle.NoPen))

        grid = "#eef3f8"

        # X 轴：时间轴
        self._axis_x = QDateTimeAxis()
        self._axis_x.setFormat("MM-dd HH:mm")
        self._axis_x.setTickCount(6)
        self._axis_x.setTitleText("时间")
        self._axis_x.setGridLineColor(QColor(grid))
        self._axis_x.setLabelsColor(QColor(theme.HEX["MUTED"]))
        self._axis_x.setTitleBrush(QBrush(QColor(theme.HEX["MUTED"])))
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)

        # Y 轴：数值
        self._axis_y = QValueAxis()
        self._axis_y.setTickCount(5)
        self._axis_y.setGridLineColor(QColor(grid))
        self._axis_y.setLabelsColor(QColor(theme.HEX["MUTED"]))
        self._axis_y.setTitleBrush(QBrush(QColor(theme.HEX["MUTED"])))  # 标题颜色（单参数时显示）
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)

        # 按参数名分组数据（一次遍历，避免 O(N×M) 重复扫描）
        all_params = store.sample_params()
        name_to_idx = {p["name"]: i for i, p in enumerate(all_params)}

        # 收集每个参数的所有点（跳过 NULL 值）。
        # 用 datetime.strptime 解析时间戳（比 QDateTime.fromString 快几十倍），
        # 同时记录全局 min/max 时间戳和 Y 值，供坐标轴范围直接复用，避免二次遍历。
        from datetime import datetime as _dt
        from PySide6.QtCore import QPointF
        grouped: dict[str, list[tuple[float, float]]] = {name: [] for name in param_names}
        min_ts: int | None = None
        max_ts: int | None = None
        y_lo: float | None = None
        y_hi: float | None = None
        for row in rows:
            name = row["param_name"]
            if name not in grouped:
                continue
            val = row["value"]
            if val is None:
                continue  # 采到但无效，曲线断开此点
            # 时间戳解析：兼容带/不带毫秒两种格式（毫秒不足 3 位补齐）
            ts_str = row["timestamp"]
            try:
                if "." in ts_str:
                    # 带毫秒：补齐到 6 位微秒以满足 strptime %f
                    head, _, frac = ts_str.partition(".")
                    frac = (frac + "000000")[:6]
                    parsed = _dt.strptime(f"{head}.{frac}", "%Y-%m-%d %H:%M:%S.%f")
                else:
                    parsed = _dt.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                ts_ms = int(parsed.timestamp() * 1000)
            except ValueError:
                continue  # 时间格式异常，跳过该点
            grouped[name].append((float(ts_ms), float(val)))
            # 更新全局范围（一次遍历内完成，供坐标轴复用）
            if min_ts is None or ts_ms < min_ts:
                min_ts = ts_ms
            if max_ts is None or ts_ms > max_ts:
                max_ts = ts_ms
            if y_lo is None or val < y_lo:
                y_lo = val
            if y_hi is None or val > y_hi:
                y_hi = val

        # 单参数最大点数：超过则等间隔降采样（曲线趋势不变，绘制量大幅下降）
        MAX_POINTS = 200

        def _downsample(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
            """等间隔抽样：保留首尾点，中间按步长取点，曲线形状不变形"""
            n = len(pts)
            if n <= MAX_POINTS:
                return pts
            step = n / MAX_POINTS
            indices = sorted(set(int(i * step) for i in range(MAX_POINTS)) | {n - 1})
            return [pts[i] for i in indices]

        for name in param_names:
            series = QLineSeries()
            idx = name_to_idx.get(name, 0)
            color = PALETTE[idx % len(PALETTE)]
            series.setColor(QColor(color))
            pen = series.pen()
            pen.setWidthF(1.6)
            series.setPen(pen)

            # 降采样后转 QPointF（避免 QtCharts 绘制过多点导致卡顿）
            sampled = _downsample(grouped[name])
            pts = [QPointF(x, y) for x, y in sampled]
            if pts:
                series.replace(pts)
                self._chart.addSeries(series)
                series.attachAxis(self._axis_x)
                series.attachAxis(self._axis_y)

        # X 轴范围（复用分组时记录的 min/max 时间戳，无需二次遍历解析）
        if min_ts is not None and max_ts is not None:
            self._axis_x.setRange(
                QDateTime.fromMSecsSinceEpoch(min_ts),
                QDateTime.fromMSecsSinceEpoch(max_ts),
            )

        # Y 轴标题：仅 1 个参数时显示"名称 (单位)"，与实时监控页一致；
        # 2 个及以上参数单位可能不同，不显示标题。
        if len(param_names) == 1:
            p = next((x for x in all_params if x["name"] == param_names[0]), {})
            display = p.get("display", "") or p.get("name", "")
            unit = p.get("unit", "")
            self._axis_y.setTitleText(f"{display} ({unit})" if unit else display)
        else:
            self._axis_y.setTitleText("")

        # Y 轴范围（复用分组时记录的 min/max Y 值，无需二次遍历）
        if y_lo is not None and y_hi is not None:
            margin = (y_hi - y_lo) * 0.1 if y_hi > y_lo else 1
            self._axis_y.setRange(y_lo - margin, y_hi + margin)

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setFrameShape(QFrame.Shape.NoFrame)
        # 图表视图白底：chart 本身透明，view 不设白底会透出页面灰色
        self._chart_view.setStyleSheet("background: #ffffff; border: none;")
        self._chart_view.setBackgroundBrush(QBrush(QColor("#ffffff")))
        self.chart_container.layout().addWidget(self._chart_view)

    # ===== 导出 =====

    @staticmethod
    def _normalize_ts(ts: str) -> str:
        """将 timestamp 统一为完整 ISO 格式 YYYY-MM-DD HH:MM:SS.mmm。

        兼容三种输入：带毫秒、不带毫秒、ISO 'T' 分隔符。
        """
        if not ts:
            return ""
        s = ts.strip().replace("T", " ")
        # 无毫秒 → 补 .000
        if "." not in s:
            return f"{s}.000"
        # 毫秒位数不足 3 位 → 右侧补零
        date_part, _, ms_part = s.partition(".")
        if len(ms_part) < 3:
            ms_part = ms_part.ljust(3, "0")
        else:
            ms_part = ms_part[:3]
        return f"{date_part}.{ms_part}"

    def _export(self):
        """导出 CSV（宽表格式）

        每个时间戳一行，每个参数一列，便于在同一行查看同一时刻的多个采样值。
        时间列用 ="..." 写法避免被 Excel 自动识别为时间类型导致毫秒丢失。
        表头示例：时间 | 温度(°C) | 压力(MPa) | 流量(m³/h)
        """
        rows = self._last_rows
        if not rows:
            QMessageBox.warning(self, "导出", "请先查询数据")
            return

        default_name = f"history_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "导出历史数据", default_name, "CSV 文件 (*.csv)")
        if not path:
            return

        try:
            # 参数名 → (display, unit) 映射
            param_map = {
                p["name"]: {
                    "display": p.get("display", "") or p["name"],
                    "unit": p.get("unit", "") or "",
                }
                for p in store.sample_params()
            }

            # 1. 收集所有出现的参数名（保持查询选中的顺序）
            seen_params: list[str] = []
            param_set: set[str] = set()
            for row in rows:
                name = row["param_name"]
                if name not in param_set:
                    param_set.add(name)
                    seen_params.append(name)

            # 2. 按时间戳分组：{timestamp: {param_name: value}}
            # 用列表保持时间先后顺序（rows 已按时间升序排列）
            time_order: list[str] = []
            time_map: dict[str, dict[str, float]] = {}
            for row in rows:
                ts = self._normalize_ts(row.get("timestamp", ""))
                if ts not in time_map:
                    time_map[ts] = {}
                    time_order.append(ts)
                time_map[ts][row["param_name"]] = row["value"]

            # 3. 构造表头：时间 | 参数名(单位) | ...
            #    表头右填充全角空格撑宽列，Excel 默认列宽即可显示完整内容，
            #    避免用户每次打开都要手动拉宽列。
            FULLWIDTH_SPACE = "　"  # U+3000，Excel 中占一个汉字宽度，撑宽最稳
            header = ["时间" + FULLWIDTH_SPACE * 12]  # 容纳 ="2026-07-30 10:00:00.000"
            for name in seen_params:
                pinfo = param_map.get(name, {})
                display = pinfo.get("display", name)
                unit = pinfo.get("unit", "")
                label = f"{display}({unit})" if unit else display
                # 填充到容纳标签 + 数值(如 -12.3456)的宽度，最少 4 个全角空格
                pad = max(4, 12 - len(label))
                header.append(label + FULLWIDTH_SPACE * pad)

            # 4. 写入：每个时间戳一行，NULL 值（采到但无效）显示为 NaN，未采样留空
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                for ts in time_order:
                    line = [f'="{ts}"']  # ="..." 防止 Excel 自动转日期类型
                    vals = time_map[ts]
                    for name in seen_params:
                        v = vals.get(name)
                        if v is None:
                            line.append("NaN")  # 采到了但值无效（NULL）
                        else:
                            line.append(f"{v:.4f}")
                    writer.writerow(line)

            QMessageBox.information(
                self, "导出成功",
                f"已导出 {len(time_order)} 个时间点 × {len(seen_params)} 个参数到\n{path}"
            )
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))
