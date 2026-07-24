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
from PySide6.QtCore import Qt, QDateTime, QEvent, QModelIndex, QAbstractItemModel
from PySide6.QtGui import QColor, QPainter, QWheelEvent

from .. import theme
from ..store import store
from .. import history_db

PALETTE = ["#0b6fb3", "#11875d", "#b86b00", "#bf3a46", "#617083", "#07588e"]


class NoWheelComboBox(QComboBox):
    """禁用鼠标滚轮的下拉框"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class CheckableComboBox(QComboBox):
    """多选下拉框：点击选项切换勾选，不关闭弹层。
    触发器显示已选汇总（如"温度、压力"），全不选时显示 placeholder。
    """
    def __init__(self, placeholder: str = "请选择"):
        super().__init__()
        self._placeholder = placeholder
        self.setEditable(True)
        self.setEditText(placeholder)

    def add_items(self, items: list[str]):
        """添加选项（默认全选）"""
        for i, text in enumerate(items):
            self.addItem(text)
            item = self.model().item(i, 0)
            item.setCheckState(Qt.CheckState.Checked)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self._update_text()

    def get_selected(self) -> list[str]:
        """返回已选项文本列表"""
        result = []
        for i in range(self.count()):
            item = self.model().item(i, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                result.append(item.text())
        return result

    def _update_text(self):
        """更新显示文本"""
        selected = self.get_selected()
        if selected:
            self.setEditText("、".join(selected))
        else:
            self.setEditText(self._placeholder)

    def showPopup(self):
        """弹出"""
        super().showPopup()

    def hidePopup(self):
        """关闭弹层时恢复汇总文本"""
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
        range_lbl.setStyleSheet(f"color: {theme.HEX['MUTED']}; font-size: {theme.FS_SM}pt; font-weight: {theme.FW_BOLD};")
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

        # card-body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(10, 10, 10, 10)

        # 空态提示
        self.empty_label = QLabel('📈  请点击"查询"加载数据')
        self.empty_label.setObjectName("empty-state")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setMinimumHeight(200)
        bl.addWidget(self.empty_label)

        # QtCharts 容器（初始隐藏，查询后显示）
        self.chart_container = QWidget()
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
        self._chart.layout().setContentsMargins(0, 0, 0, 0)
        self._chart.setBackgroundVisible(False)
        self._chart.setPlotAreaBackgroundVisible(True)
        self._chart.setPlotAreaBackgroundBrush(__import__("PySide6.QtGui", fromlist=["QBrush"]).QBrush(QColor("#fbfdff")))
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
        self._axis_x.setTitleBrush(__import__("PySide6.QtGui", fromlist=["QBrush"]).QBrush(QColor(theme.HEX["MUTED"])))
        self._chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)

        # Y 轴：数值
        self._axis_y = QValueAxis()
        self._axis_y.setTickCount(5)
        self._axis_y.setGridLineColor(QColor(grid))
        self._axis_y.setLabelsColor(QColor(theme.HEX["MUTED"]))
        self._chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)

        # 按参数名分组数据
        all_params = store.sample_params()
        name_to_idx = {p["name"]: i for i, p in enumerate(all_params)}

        from PySide6.QtCore import QPointF
        for name in param_names:
            series = QLineSeries()
            idx = name_to_idx.get(name, 0)
            color = PALETTE[idx % len(PALETTE)]
            series.setColor(QColor(color))
            pen = series.pen()
            pen.setWidthF(1.6)
            series.setPen(pen)

            # 添加数据点
            pts = []
            for row in rows:
                if row["param_name"] == name:
                    dt = QDateTime.fromString(row["timestamp"], "yyyy-MM-dd HH:mm:ss.zzz")
                    if not dt.isValid():
                        dt = QDateTime.fromString(row["timestamp"], "yyyy-MM-dd HH:mm:ss")
                    ts_ms = dt.toMSecsSinceEpoch()
                    pts.append(QPointF(float(ts_ms), float(row["value"])))
            if pts:
                series.replace(pts)
                self._chart.addSeries(series)
                series.attachAxis(self._axis_x)
                series.attachAxis(self._axis_y)

        # X 轴范围
        if rows:
            times = []
            for row in rows:
                dt = QDateTime.fromString(row["timestamp"], "yyyy-MM-dd HH:mm:ss.zzz")
                if not dt.isValid():
                    dt = QDateTime.fromString(row["timestamp"], "yyyy-MM-dd HH:mm:ss")
                times.append(dt)
            self._axis_x.setRange(min(times), max(times))

        # Y 轴范围（自动）
        values = [row["value"] for row in rows]
        if values:
            lo, hi = min(values), max(values)
            margin = (hi - lo) * 0.1 if hi > lo else 1
            self._axis_y.setRange(lo - margin, hi + margin)

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setFrameShape(QFrame.Shape.NoFrame)
        self.chart_container.layout().addWidget(self._chart_view)

    # ===== 导出 =====

    def _export(self):
        """导出 CSV"""
        rows = self._last_rows
        if not rows:
            QMessageBox.warning(self, "导出", "请先查询数据")
            return

        default_name = f"history_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "导出历史数据", default_name, "CSV 文件 (*.csv)")
        if not path:
            return

        try:
            name_map = {p["name"]: p.get("display", "") or p["name"] for p in store.sample_params()}
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["时间", "参数", "数值"])
                for row in rows:
                    writer.writerow([
                        row["timestamp"],
                        name_map.get(row["param_name"], row["param_name"]),
                        f"{row['value']:.4f}",
                    ])
            QMessageBox.information(self, "导出成功", f"已导出 {len(rows)} 条到\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))
