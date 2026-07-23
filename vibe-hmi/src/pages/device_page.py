"""
设备管理页

参考参数配置页布局：上卡设备列表表格（增删勾选）+ 下卡编辑表单（新增/编辑设备）。
设备列表持久化到 config/devices.json。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QGridLayout, QLineEdit,
    QMessageBox, QAbstractItemView, QHeaderView, QCheckBox,
    QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from .. import theme
from ..store import store

COLS = ["", "设备名称", "从站地址", "参数数量", "设备位置", "描述"]


class DevicePage(QWidget):
    """设备管理页：上卡设备列表 + 下卡编辑表单"""

    # 设备列表变化时发射（供参数页/监控页刷新下拉框）
    devices_changed = Signal()

    def __init__(self):
        super().__init__()
        self._edit_mode = "create"  # 'create' | 'edit'
        self._editing_id = None
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        """整个页面可滚动：设备列表（上）+ 编辑表单（下），上下堆叠"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 上卡：设备列表表格
        layout.addWidget(self._build_list_card())

        # 下卡：编辑表单
        layout.addWidget(self._build_form_card())

        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ===== 上卡：设备列表 =====

    def _build_list_card(self) -> QFrame:
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
        title = QLabel("设备列表")
        title.setObjectName("card-title")
        self.count_tag = QLabel("")
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
        bl.setSpacing(8)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.btn_create = QPushButton("新增设备")
        self.btn_edit = QPushButton("编辑勾选")
        self.btn_edit.setProperty("variant", "secondary")
        self.btn_edit.setEnabled(False)
        self.btn_delete = QPushButton("删除勾选")
        self.btn_delete.setProperty("variant", "danger")
        self.btn_delete.setEnabled(False)

        self.btn_create.clicked.connect(lambda: self._set_edit_mode("create"))
        self.btn_edit.clicked.connect(lambda: self._set_edit_mode("edit"))
        self.btn_delete.clicked.connect(self._delete_selected)

        toolbar.addWidget(self.btn_create)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        bl.addLayout(toolbar)

        # 设备表
        self.table = InnerScrollTable()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # 各列固定宽度（描述列拉伸填充剩余空间）
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 130)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 80)   # 参数数量
        self.table.setColumnWidth(4, 120)  # 设备位置
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # 描述列拉伸
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setVisible(False)
        # 固定高度（约 5 行可见 + 表头）
        self.table.setMinimumHeight(210)
        self.table.setMaximumHeight(210)
        bl.addWidget(self.table)

        cl.addWidget(body, 1)
        return card

    # ===== 下卡：编辑表单 =====

    def _build_form_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        head = QFrame()
        head.setObjectName("card-head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(10, 0, 10, 0)
        self.form_title = QLabel("新增设备")
        self.form_title.setObjectName("card-title")
        form_tag = QLabel("表单")
        form_tag.setObjectName("tag")
        form_tag.setFixedHeight(18)
        hl.addWidget(self.form_title)
        hl.addStretch()
        hl.addWidget(form_tag, alignment=Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(head)

        body = QWidget()
        form = QGridLayout(body)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(14)
        form.setHorizontalSpacing(12)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)

        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("如：设备1")
        self.f_slave = QLineEdit()
        self.f_slave.setText("1")
        self.f_slave.setPlaceholderText("1-247")
        self.f_location = QLineEdit()
        self.f_location.setPlaceholderText("如：1号车间")
        self.f_desc = QLineEdit()
        self.f_desc.setPlaceholderText("可选")

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

        row = 0
        form.addWidget(field("设备名称", self.f_name), row, 0)
        form.addWidget(field("从站地址 (1-247)", self.f_slave), row, 1)
        row += 1
        form.addWidget(field("设备位置", self.f_location), row, 0)
        form.addWidget(field("描述（可选）", self.f_desc), row, 1)
        row += 1

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_save = QPushButton("保存设备")
        self.btn_cancel = QPushButton("取消修改")
        self.btn_cancel.setProperty("variant", "secondary")
        self.btn_save.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addStretch()
        form.addLayout(btn_row, row, 0, 1, 4)

        cl.addWidget(body, 1)
        return card

    # ===== 表格刷新 =====

    def _refresh_table(self):
        """重建设备表 + 更新计数 tag + 按钮状态"""
        self.table.clearContents()
        self.table.setRowCount(0)
        self.table.setRowCount(len(store.devices))
        for row, d in enumerate(store.devices):
            # checkbox（居中）
            cb_container = QWidget()
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb = QCheckBox()
            cb.stateChanged.connect(self._update_toolbar_state)
            cb_layout.addWidget(cb)
            self.table.setCellWidget(row, 0, cb_container)
            # 数据列：设备名称、从站地址、参数数量、设备位置、描述
            vals = [d.get("name", ""), str(d.get("slave_id", 1)),
                    str(store.param_count(d["id"])),
                    d.get("location", ""), d.get("desc", "")]
            for col, val in enumerate(vals, 1):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)

        # 更新计数 tag
        count = len(store.devices)
        self.count_tag.setText(f"{count} 台")
        self.count_tag.setProperty("variant", "ok" if count > 0 else "warn")
        self.count_tag.style().polish(self.count_tag)

        self._update_toolbar_state()

    # ===== 工具栏状态 =====

    def _checked_rows(self) -> list[int]:
        """获取勾选的行号"""
        rows = []
        for row in range(self.table.rowCount()):
            container = self.table.cellWidget(row, 0)
            if container:
                cb = container.findChild(QCheckBox)
                if cb and cb.isChecked():
                    rows.append(row)
        return rows

    def _update_toolbar_state(self):
        checked = self._checked_rows()
        self.btn_edit.setEnabled(len(checked) == 1)
        self.btn_delete.setEnabled(len(checked) >= 1)

    # ===== 编辑模式 =====

    def _set_edit_mode(self, mode: str):
        self._edit_mode = mode
        if mode == "create":
            self._editing_id = None
            self.form_title.setText("新增设备")
            self._clear_form()
            # 清空所有勾选
            for row in range(self.table.rowCount()):
                container = self.table.cellWidget(row, 0)
                if container:
                    cb = container.findChild(QCheckBox)
                    if cb:
                        cb.setChecked(False)
            self._update_toolbar_state()
        elif mode == "edit":
            checked = self._checked_rows()
            if len(checked) != 1:
                return
            d = store.devices[checked[0]]
            self._editing_id = d["id"]
            self.form_title.setText(f'编辑设备：{d["name"]}')
            self._load_form(d)

    def _clear_form(self):
        self.f_name.clear()
        self.f_slave.setText("1")
        self.f_location.clear()
        self.f_desc.clear()

    def _load_form(self, d: dict):
        self.f_name.setText(d.get("name", ""))
        self.f_slave.setText(str(d.get("slave_id", 1)))
        self.f_location.setText(d.get("location", ""))
        self.f_desc.setText(d.get("desc", ""))

    def _save(self):
        name = self.f_name.text().strip()
        if not name:
            QMessageBox.warning(self, "保存失败", "设备名称不能为空")
            return
        try:
            slave_id = int(self.f_slave.text().strip())
            if not (1 <= slave_id <= 247):
                QMessageBox.warning(self, "保存失败", "从站地址范围 1-247")
                return
        except ValueError:
            QMessageBox.warning(self, "保存失败", "从站地址必须是数字")
            return
        location = self.f_location.text().strip()
        desc = self.f_desc.text().strip()

        if self._edit_mode == "edit" and self._editing_id:
            store.update_device(self._editing_id, name, slave_id, desc, location)
        else:
            store.add_device(name, slave_id, desc, location)

        self._refresh_table()
        self._set_edit_mode("create")
        self.devices_changed.emit()

    def _delete_selected(self):
        checked = self._checked_rows()
        if not checked:
            return
        names = [store.devices[r]["name"] for r in checked]
        reply = QMessageBox.question(
            self, "删除确认",
            f"确认删除 {len(names)} 个设备：{', '.join(names)}？\n设备的所有参数将同时删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ids = [store.devices[r]["id"] for r in checked]
            for did in ids:
                store.delete_device(did)
            self._refresh_table()
            self._set_edit_mode("create")
            self.devices_changed.emit()

    def _cancel(self):
        self._set_edit_mode("create")


class InnerScrollTable(QTableWidget):
    """内部滚动表：滚轮事件始终 accept，到顶/到底也不冒泡到外层 QScrollArea"""
    def wheelEvent(self, event):
        super().wheelEvent(event)
        event.accept()
