"""
报警记录页

迁移自原型 js/pages/alarms.js。
单卡布局：card-head 显示未确认计数 tag + 按钮行 + 报警表（7 列）。

确认状态机：勾选 → 确认按钮 → acknowledged=True（不可逆，checkbox disabled）。
全选 checkbox 仅控制未确认行。
导出报警为 CSV 文件。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QCheckBox,
    QAbstractItemView, QHeaderView, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from .. import theme
from ..store import store

COLS = ["", "时间", "内容", "终端", "级别", "状态", "确认信息"]


class AlarmsPage(QWidget):
    """报警记录页"""
    # 报警确认后发射（供侧边栏标签联动）
    alarms_changed = Signal()

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self._build_card(), 1)

    def _build_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # card-head：标题 + 未确认计数 tag
        head = QFrame()
        head.setObjectName("card-head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(10, 0, 10, 0)
        title = QLabel("报警记录")
        title.setObjectName("card-title")
        self.count_tag = QLabel("")
        self.count_tag.setObjectName("tag")
        self.count_tag.setFixedHeight(18)
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(self.count_tag, alignment=Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(head)

        # body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(10, 10, 10, 10)
        bl.setSpacing(8)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_ack = QPushButton("确认勾选")
        self.btn_ack.setEnabled(False)
        self.btn_ack.clicked.connect(self._ack_selected)
        self.btn_ack_all = QPushButton("确认全部未确认")
        self.btn_ack_all.setProperty("variant", "secondary")
        self.btn_ack_all.clicked.connect(self._ack_all)
        self.btn_delete = QPushButton("删除选中")
        self.btn_delete.setProperty("variant", "secondary")
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_export = QPushButton("导出报警")
        self.btn_export.setProperty("variant", "secondary")
        self.btn_export.clicked.connect(self._export)
        btn_row.addWidget(self.btn_ack)
        btn_row.addWidget(self.btn_ack_all)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_export)
        btn_row.addStretch()
        bl.addLayout(btn_row)

        # 报警表
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().resizeSection(0, 40)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setVisible(False)
        bl.addWidget(self.table)
        cl.addWidget(body, 1)
        return card

    def _refresh_table(self):
        """重建报警表 + 更新计数 tag + 按钮状态"""
        self.table.clearContents()
        self.table.setRowCount(0)
        alarms = store.alarms
        self.table.setRowCount(len(alarms))

        # 表头全选 checkbox（仅控制未确认行）
        header_cb = QCheckBox()
        header_cb.setObjectName("alarm-check-all")
        header_cb.stateChanged.connect(self._on_check_all)
        header_container = QWidget()
        hcl = QHBoxLayout(header_container)
        hcl.setContentsMargins(0, 0, 0, 0)
        hcl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hcl.addWidget(header_cb)
        self.table.setCellWidget(0, 0, header_container) if alarms else None
        self._header_cb = header_cb

        for row, a in enumerate(alarms):
            # checkbox：所有行都可勾选（已确认行也可勾选用于删除）
            acked = a.get("acknowledged", False)
            cb_container = QWidget()
            cbl = QHBoxLayout(cb_container)
            cbl.setContentsMargins(0, 0, 0, 0)
            cbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb = QCheckBox()
            cb.setEnabled(True)  # 已确认行也允许勾选（用于删除）
            cb.stateChanged.connect(self._update_btn_state)
            cbl.addWidget(cb)
            self.table.setCellWidget(row, 0, cb_container)

            # 数据列
            status_text = "已确认" if acked else "未确认"
            status_color = theme.HEX["MUTED"] if acked else theme.HEX["WARN"]
            ack_info = f'{a.get("ack_user", "")} {a.get("ack_time", "")}' if acked else "—"

            vals = [a["time"], a["content"], a["terminal"], a["level"], status_text, ack_info]
            for col, val in enumerate(vals, 1):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if col == 5:  # 状态列着色
                    item.setForeground(QColor(status_color))
                self.table.setItem(row, col, item)

        self._update_count_tag()
        self._update_btn_state()

    def _update_count_tag(self):
        """更新未确认计数 tag"""
        count = store.unack_count()
        if count > 0:
            self.count_tag.setText(f"{count} 未确认")
            self.count_tag.setProperty("variant", "warn")
        else:
            self.count_tag.setText("全部已确认")
            self.count_tag.setProperty("variant", "ok")
        self.count_tag.style().polish(self.count_tag)

    def _update_btn_state(self):
        """更新确认按钮启用状态"""
        # "确认勾选"只对未确认的勾选行生效
        unack_checked = self._checked_unack_rows()
        self.btn_ack.setEnabled(len(unack_checked) > 0)
        # 确认全部按钮：有未确认时启用
        self.btn_ack_all.setEnabled(store.unack_count() > 0)

    def _checked_rows(self) -> list[int]:
        """获取所有勾选的行号（含已确认行，供删除用）"""
        rows = []
        for row in range(self.table.rowCount()):
            container = self.table.cellWidget(row, 0)
            if container:
                cb = container.findChild(QCheckBox)
                if cb and cb.isChecked():
                    rows.append(row)
        return rows

    def _checked_unack_rows(self) -> list[int]:
        """获取勾选且未确认的行号（供"确认"操作用，已确认的跳过）"""
        rows = []
        alarms = store.alarms
        for row in range(self.table.rowCount()):
            if row >= len(alarms):
                continue
            if alarms[row].get("acknowledged", False):
                continue  # 已确认的跳过
            container = self.table.cellWidget(row, 0)
            if container:
                cb = container.findChild(QCheckBox)
                if cb and cb.isChecked():
                    rows.append(row)
        return rows

    def _on_check_all(self, state):
        """表头全选 checkbox：切换所有行（含已确认，用于批量删除）"""
        checked = state == Qt.CheckState.Checked.value
        for row in range(self.table.rowCount()):
            container = self.table.cellWidget(row, 0)
            if container:
                cb = container.findChild(QCheckBox)
                if cb:
                    cb.blockSignals(True)
                    cb.setChecked(checked)
                    cb.blockSignals(False)
        self._update_btn_state()

    def _ack_selected(self):
        """确认勾选的报警（仅未确认行生效）"""
        rows = self._checked_unack_rows()
        if not rows:
            return
        alarm_ids = [store.alarms[r]["id"] for r in rows]
        store.acknowledge(alarm_ids)
        self._refresh_table()
        self.alarms_changed.emit()

    def _ack_all(self):
        """确认全部未确认报警"""
        ids = [a["id"] for a in store.alarms if not a.get("acknowledged")]
        if not ids:
            return
        reply = QMessageBox.question(
            self, "确认全部",
            f"确认全部 {len(ids)} 条未确认报警？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            store.acknowledge(ids)
            self._refresh_table()
            self.alarms_changed.emit()

    def _delete_selected(self):
        """删除勾选的报警行（含已确认的，所有勾选行都可删）。"""
        rows = self._checked_rows()  # 所有勾选行（含已确认）
        if not rows:
            QMessageBox.information(self, "删除报警", "请先勾选要删除的报警（左侧复选框）")
            return
        alarms = store.alarms
        ids = [alarms[r]["id"] for r in rows if r < len(alarms)]
        if not ids:
            return

        reply = QMessageBox.question(
            self, "删除报警",
            f"确认删除勾选的 {len(ids)} 条报警？\n此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 逐条删除（store.delete_alarm 内部已 reload 内存）
        deleted = sum(1 for aid in ids if store.delete_alarm(aid))
        self._refresh_table()
        self.alarms_changed.emit()
        if deleted > 0:
            QMessageBox.information(self, "删除完成", f"已删除 {deleted} 条报警")

    @staticmethod
    def _normalize_ts(ts: str) -> str:
        """将时间统一为完整格式 YYYY-MM-DD HH:MM:SS.mmm。

        与历史数据 CSV 的 _normalize_ts 保持一致：
        兼容带毫秒、不带毫秒、ISO 'T' 分隔符三种输入。
        """
        if not ts:
            return ""
        s = ts.strip().replace("T", " ")
        if "." not in s:
            return f"{s}.000"
        date_part, _, ms_part = s.partition(".")
        if len(ms_part) < 3:
            ms_part = ms_part.ljust(3, "0")
        else:
            ms_part = ms_part[:3]
        return f"{date_part}.{ms_part}"

    def _export(self):
        """导出报警为 CSV

        时间列格式与历史数据 CSV 一致：="YYYY-MM-DD HH:MM:SS.mmm"
        （补齐 3 位毫秒 + ="..." 包装防 Excel 自动转日期类型导致毫秒丢失）。
        """
        path, _ = QFileDialog.getSaveFileName(
            self, "导出报警", "alarms.csv", "CSV 文件 (*.csv)"
        )
        if not path:
            return
        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["时间", "内容", "终端", "级别", "状态", "确认人", "确认时间"])
                for a in store.alarms:
                    ts = f'="{self._normalize_ts(a.get("time", ""))}"'
                    writer.writerow([
                        ts, a["content"], a["terminal"], a["level"],
                        "已确认" if a.get("acknowledged") else "未确认",
                        a.get("ack_user", ""), a.get("ack_time", ""),
                    ])
            QMessageBox.information(self, "导出成功", f"已导出 {len(store.alarms)} 条报警到\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))
