"""
设备总览页

迁移自原型 js/pages/overview.js。
布局：卡片A 运行总览（4 metric）+ 卡片B 快捷操作（4 quick-card）+ 卡片C 设备列表表（7 列）。

metric 数值动态计算：串口名来自 store.current_port，在线/告警数从 store.devices filter。
快捷卡点击跳转对应页面。设备表行点击选中高亮。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from .. import theme
from ..store import store


class OverviewPage(QWidget):
    """设备总览页"""

    # 快捷卡点击跳转信号
    page_clicked = Signal(str)

    def __init__(self):
        super().__init__()
        self._metric_values: dict[str, QLabel] = {}  # label → value QLabel（供刷新）
        self._conn_tag: QLabel | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 上半部分：运行总览 + 快捷操作（左右并排）
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.addWidget(self._build_metric_card())
        top_row.addWidget(self._build_quick_card())
        layout.addLayout(top_row)

        # 下半部分：设备列表
        layout.addWidget(self._build_device_table(), 1)

    def showEvent(self, event):
        """每次显示页面时刷新动态值"""
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        """刷新 metric 动态数值（串口/在线/告警）+ 连接状态 tag"""
        from ..serial.serial_manager import serial_manager
        # 当前串口 + 连接状态
        connected = serial_manager.is_connected
        if connected:
            port = store.current_port or serial_manager._serial.portstr if serial_manager._serial else "—"
            status = "已连接"
            status_color = theme.HEX["OK"]
        else:
            port = "—"
            status = "未连接"
            status_color = theme.HEX["WARN"]
        if "当前串口" in self._metric_values:
            self._metric_values["当前串口"].setText(
                f'{port}<small style="color:{status_color}"> {status}</small>'
            )
        # 在线设备数（当前所有设备都算在线）
        online = len(store.devices)
        if "在线设备" in self._metric_values:
            self._metric_values["在线设备"].setText(
                f'{online}<small style="color:{theme.HEX["MUTED"]}"> 台</small>'
            )
        # 当前告警数（未确认报警）
        alarms = store.unack_count()
        if "当前告警" in self._metric_values:
            color = theme.HEX["WARN"] if alarms > 0 else theme.HEX["OK"]
            self._metric_values["当前告警"].setText(
                f'<span style="color:{color};">{alarms}</span>'
                f'<small style="color:{theme.HEX["MUTED"]}"> 条</small>'
            )
        # 连接状态 tag
        if self._conn_tag:
            if connected:
                self._conn_tag.setText("在线")
                self._conn_tag.setProperty("variant", "ok")
            else:
                self._conn_tag.setText("未连接")
                self._conn_tag.setProperty("variant", "warn")
            self._conn_tag.style().polish(self._conn_tag)

    def _build_metric_card(self) -> QFrame:
        """卡片A 运行总览：4 个 metric"""
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        head, self._conn_tag = self._make_card_head_with_tag("运行总览", "在线", "ok")
        cl.addWidget(head)

        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        labels = ["当前串口", "在线设备", "当前告警", "离线阈值"]
        units = ["", "台", "条", "min"]
        defaults = ["—", "—", "—", "10"]
        for i, (label, unit, default) in enumerate(zip(labels, units, defaults)):
            row, col = divmod(i, 2)
            m, val_label = self._make_metric(label, default, unit)
            self._metric_values[label] = val_label
            grid.addWidget(m, row, col)
        cl.addWidget(body, 1)
        return card

    def _build_quick_card(self) -> QFrame:
        """卡片B 快捷操作：4 个快捷卡按钮"""
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        head = self._make_card_head("快捷操作", "", "")
        cl.addWidget(head)

        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        quick_items = [
            ("设备连接", "serial"),
            ("实时监控", "monitor"),
            ("报警记录", "alarms"),
            ("历史数据", "history"),
        ]
        for i, (name, page_id) in enumerate(quick_items):
            row, col = divmod(i, 2)
            btn = QPushButton(name)
            btn.setObjectName("quick-card")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, pid=page_id: self.page_clicked.emit(pid))
            grid.addWidget(btn, row, col)
        cl.addWidget(body, 1)
        return card

    def _build_device_table(self) -> QFrame:
        """卡片C 设备列表"""
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        online = sum(1 for d in store.devices)
        head = self._make_card_head("设备列表", f"{online} 台", "ok")
        cl.addWidget(head)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(10, 10, 10, 10)

        cols = ["设备名称", "从站地址", "描述", "参数数量"]
        self.table = QTableWidget()
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setVisible(False)
        self.table.setRowCount(len(store.devices))

        for row, d in enumerate(store.devices):
            vals = [d.get("name", ""), str(d.get("slave_id", 1)),
                    d.get("desc", ""), str(store.param_count(d["id"]))]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)
                self.table.setItem(row, col, item)
        bl.addWidget(self.table)
        cl.addWidget(body, 1)
        return card

    # ===== 辅助方法 =====

    def _make_card_head(self, title: str, tag_text: str, tag_variant: str) -> QFrame:
        head, _ = self._make_card_head_with_tag(title, tag_text, tag_variant)
        return head

    def _make_card_head_with_tag(self, title: str, tag_text: str, tag_variant: str):
        """返回 (head QFrame, tag QLabel)，tag QLabel 供后续刷新"""
        head = QFrame()
        head.setObjectName("card-head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel(title)
        lbl.setObjectName("card-title")
        hl.addWidget(lbl)
        hl.addStretch()
        tag = None
        if tag_text:
            tag = QLabel(tag_text)
            tag.setObjectName("tag")
            if tag_variant:
                tag.setProperty("variant", tag_variant)
            tag.setFixedHeight(18)
            hl.addWidget(tag, alignment=Qt.AlignmentFlag.AlignVCenter)
        return head, tag

    def _make_metric(self, label: str, value: str, unit: str):
        """返回 (QFrame, value QLabel)，value QLabel 供后续刷新"""
        m = QFrame()
        m.setObjectName("metric")
        lay = QVBoxLayout(m)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setObjectName("metric-label")
        val = QLabel(f'{value}<small style="color:{theme.HEX["MUTED"]}"> {unit}</small>')
        val.setObjectName("metric-value")
        val.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(lbl)
        lay.addWidget(val, 1)
        return m, val
