"""
参数配置页

迁移自原型 js/pages/params.js。
左卡：参数表（QTableWidget 11 列）+ 工具栏（新增/编辑/删除 + 分类筛选）
右卡：编辑表单（QFormLayout）+ 保存/取消

CRUD 走 store（持久化 JSON），校验规则（名称唯一/地址合法hex且不重复/min<=max等）。
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QLineEdit, QSpinBox, QCheckBox,
    QFormLayout, QFrame, QMessageBox, QAbstractItemView, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QWheelEvent
from .. import theme
from ..store import store


class NoWheelComboBox(QComboBox):
    """禁用鼠标滚轮修改的下拉框（防止误操作）"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class NoWheelSpinBox(QSpinBox):
    """禁用鼠标滚轮修改的数字框（防止误操作）"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class InnerScrollTable(QTableWidget):
    """内部滚动表：滚轮事件始终 accept，到顶/到底也不冒泡到外层 QScrollArea"""
    def wheelEvent(self, event: QWheelEvent):
        # 先交给基类处理（表格内部正常滚动）
        super().wheelEvent(event)
        # 无论是否到边界，都吞掉事件，避免冒泡触发外层页面滚动
        event.accept()


class StatusChip(QFrame):
    """胶囊状态标签（圆点 + 文字），和监控页 curve-chip 风格统一。

    variant: "" 默认灰 / "ok" 绿 / "warn" 橙
    """

    def __init__(self, text: str, variant: str = ""):
        super().__init__()
        self.setObjectName("status-chip")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(26)
        self._variant = variant

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(6)

        # 颜色映射
        colors = {
            "ok": theme.HEX["OK"],
            "warn": theme.HEX["WARN"],
            "": theme.HEX["MUTED"],
        }
        bgs = {
            "ok": theme.HEX["TAG_OK_BG"],
            "warn": theme.HEX["TAG_WARN_BG"],
            "": theme.HEX["TAG_BG"],
        }
        color = colors.get(variant, theme.HEX["MUTED"])
        bg = bgs.get(variant, theme.HEX["TAG_BG"])

        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        self._dot.setStyleSheet(f"background: {color}; border-radius: 4px; border: none;")
        self._text = QLabel(text)
        self._text.setStyleSheet(
            f"color: {color}; font-size: {theme.FS_SM}pt; "
            f"font-weight: {theme.FW_BOLD}; border: none; background: transparent;"
        )
        lay.addWidget(self._dot)
        lay.addWidget(self._text)

        # 按变体设背景和边框（内联，确保覆盖全局 QSS）
        self.setStyleSheet(
            f"#status-chip {{ border: 1px solid {bg}; border-radius: 13px; background: {bg}; }}"
        )

    def update_state(self, text: str, variant: str = ""):
        """更新文字和颜色变体"""
        colors = {"ok": theme.HEX["OK"], "warn": theme.HEX["WARN"], "": theme.HEX["MUTED"]}
        bgs = {"ok": theme.HEX["TAG_OK_BG"], "warn": theme.HEX["TAG_WARN_BG"], "": theme.HEX["TAG_BG"]}
        color = colors.get(variant, theme.HEX["MUTED"])
        bg = bgs.get(variant, theme.HEX["TAG_BG"])
        self._dot.setStyleSheet(f"background: {color}; border-radius: 4px; border: none;")
        self._text.setText(text)
        self._text.setStyleSheet(
            f"color: {color}; font-size: {theme.FS_SM}pt; "
            f"font-weight: {theme.FW_BOLD}; border: none; background: transparent;"
        )
        self.setStyleSheet(
            f"#status-chip {{ border: 1px solid {bg}; border-radius: 13px; background: {bg}; }}"
        )


# 数据类型 / 权限 / 分类 选项
# 数据类型：显示名 → 内部值映射
TYPE_DISPLAY = ["uint8", "int16", "uint16", "int32", "uint32", "float", "bool"]
TYPE_INTERNAL = ["uint8", "int16", "uint16", "int32", "uint32", "float32", "bool"]
ACCESSES = ["只读", "只写", "读写"]
CATEGORIES = ["采样参数", "配置参数"]
CURVE_OPTIONS = ["是", "否"]

# 表格列：checkbox/参数名/显示名/地址/分类/类型/权限/单位/小数/范围/说明
COLS = ["", "参数名", "显示名", "地址", "分类", "类型", "权限", "单位", "小数", "范围", "说明"]


class ParamsPage(QWidget):
    """参数配置页"""

    # 表单 dirty 状态变化信号（dirty: bool），供侧边栏/tab 同步标签
    dirty_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self._edit_mode = "create"  # 'create' | 'edit'
        self._editing_name = None
        self._build_ui()
        self._refresh_table()
        self._set_dirty(False)  # 初始"已同步"

    def _refresh_device_combo(self):
        """刷新设备下拉框（设备增删后调用）"""
        self.combo_device.blockSignals(True)
        self.combo_device.clear()
        for d in store.devices:
            self.combo_device.addItem(f'{d["name"]} (slave {d["slave_id"]})', d["id"])
        # 选中当前设备
        idx = self.combo_device.findData(store.current_device_id)
        if idx >= 0:
            self.combo_device.setCurrentIndex(idx)
        self.combo_device.blockSignals(False)

    def _on_device_changed(self):
        """切换设备 → 更新 current_device_id + 刷新表格"""
        device_id = self.combo_device.currentData()
        if device_id and device_id != store.current_device_id:
            store.current_device_id = device_id
            self._refresh_table()
            self._set_edit_mode("create")

    def _build_ui(self):
        """整个页面可滚动：参数定义（上）+ 新增参数（下），上下堆叠"""
        # 外层滚动区域
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # 内容容器
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 上卡：参数定义表格（表格内部可滚动，卡片本身按内容高度）
        left = self._build_left_card()
        layout.addWidget(left)

        # 下卡：编辑表单（按内容高度，字段间距充足不挤）
        right = self._build_right_card()
        layout.addWidget(right)

        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ===== 左卡 =====

    def _build_left_card(self):
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # card-head
        head = QFrame()
        head.setObjectName("card-head")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(10, 0, 10, 0)
        title = QLabel("Modbus RTU 参数定义")
        title.setObjectName("card-title")
        head_layout.addWidget(title)
        head_layout.addStretch()
        # 设备切换下拉框（放在同步状态前面）
        self.combo_device = NoWheelComboBox()
        self._refresh_device_combo()
        self.combo_device.currentIndexChanged.connect(self._on_device_changed)
        head_layout.addWidget(self.combo_device, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.dirty_tag = StatusChip("已同步", "ok")
        head_layout.addWidget(self.dirty_tag, alignment=Qt.AlignmentFlag.AlignVCenter)
        card_layout.addWidget(head)

        # card-body
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(8)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_create = QPushButton("新增参数")
        self.btn_edit = QPushButton("编辑勾选")
        self.btn_edit.setProperty("variant", "secondary")
        self.btn_edit.setEnabled(False)
        self.btn_delete = QPushButton("删除勾选")
        self.btn_delete.setProperty("variant", "danger")
        self.btn_delete.setEnabled(False)
        self.btn_up = QPushButton("上移")
        self.btn_up.setProperty("variant", "secondary")
        self.btn_up.setEnabled(False)
        self.btn_down = QPushButton("下移")
        self.btn_down.setProperty("variant", "secondary")
        self.btn_down.setEnabled(False)

        self.btn_create.clicked.connect(lambda: self._set_edit_mode("create"))
        self.btn_edit.clicked.connect(lambda: self._set_edit_mode("edit"))
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_up.clicked.connect(self._move_up)
        self.btn_down.clicked.connect(self._move_down)

        toolbar.addWidget(self.btn_create)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_up)
        toolbar.addWidget(self.btn_down)
        toolbar.addStretch()

        # 分类筛选
        toolbar.addWidget(QLabel("分类筛选"))
        self.filter_combo = NoWheelComboBox()
        self.filter_combo.addItems(["全部", "采样参数", "配置参数"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.filter_combo)

        body_layout.addLayout(toolbar)

        # 参数表（固定高度，行多了内部滚动；滚轮不冒泡到外层页面）
        self.table = InnerScrollTable()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        # 表头左对齐
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # Interactive 模式：列宽固定，最后一列（说明）拉伸填充剩余空间
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        col_widths = [40, 120, 90, 80, 90, 80, 60, 60, 50, 120, 150]
        for i, w in enumerate(col_widths):
            self.table.setColumnWidth(i, w)
        # 说明列（最后一列）拉伸填充
        self.table.horizontalHeader().setSectionResizeMode(len(col_widths) - 1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # 禁用焦点虚线框
        self.table.verticalHeader().setVisible(False)  # 隐藏行号
        self.table.itemChanged.connect(self._on_table_item_changed)
        # 固定高度（约 5 行可见 + 表头），超出纵向滚动
        self.table.setMinimumHeight(210)
        self.table.setMaximumHeight(210)
        body_layout.addWidget(self.table)

        card_layout.addWidget(body, 1)
        return card

    # ===== 右卡 =====

    def _build_right_card(self):
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        head = QFrame()
        head.setObjectName("card-head")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(10, 0, 10, 0)
        self.form_title = QLabel("新增参数")
        self.form_title.setObjectName("card-title")
        form_tag = StatusChip("表单", "")
        head_layout.addWidget(self.form_title)
        head_layout.addStretch()
        head_layout.addWidget(form_tag, alignment=Qt.AlignmentFlag.AlignVCenter)
        card_layout.addWidget(head)

        body = QWidget()
        from PySide6.QtWidgets import QGridLayout
        form = QGridLayout(body)
        form.setContentsMargins(14, 14, 14, 14)
        form.setVerticalSpacing(14)
        form.setHorizontalSpacing(12)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)

        self.f_name = QLineEdit()
        self.f_display = QLineEdit()
        self.f_address = QLineEdit()
        self.f_category = NoWheelComboBox()
        self.f_category.addItems(CATEGORIES)
        self.f_type = NoWheelComboBox()
        self.f_type.addItems(TYPE_DISPLAY)
        self.f_access = NoWheelComboBox()
        self.f_access.addItems(ACCESSES)
        self.f_curve = NoWheelComboBox()
        self.f_curve.addItems(CURVE_OPTIONS)
        self.f_unit = QLineEdit()
        self.f_decimals = QLineEdit()
        self.f_decimals.setPlaceholderText("0")
        self.f_min = QLineEdit()
        self.f_max = QLineEdit()
        self.f_desc = QLineEdit()

        # 表单任一字段改动 → 标记"未保存"
        for w in (self.f_name, self.f_display, self.f_address, self.f_unit,
                  self.f_decimals, self.f_min, self.f_max, self.f_desc):
            w.textChanged.connect(self._on_form_changed)
        for cb in (self.f_category, self.f_type, self.f_access, self.f_curve):
            cb.currentTextChanged.connect(self._on_form_changed)

        def field(label_text: str, widget) -> QWidget:
            """创建 label 在上、input 在下的字段组件（对应原型 .field）"""
            f = QWidget()
            lay = QVBoxLayout(f)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(4)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {theme.HEX['MUTED']}; font-size: {theme.FS_SM}pt; font-weight: {theme.FW_BOLD};")
            lay.addWidget(lbl)
            lay.addWidget(widget)
            return f

        # 两列布局（原型 form-grid：每行 2 个字段，label 在上 input 在下）
        row = 0
        form.addWidget(field("参数名", self.f_name), row, 0)
        form.addWidget(field("显示名", self.f_display), row, 1)
        row += 1
        form.addWidget(field("Modbus 地址", self.f_address), row, 0)
        form.addWidget(field("参数分类", self.f_category), row, 1)
        row += 1
        form.addWidget(field("数据类型", self.f_type), row, 0)
        form.addWidget(field("访问权限", self.f_access), row, 1)
        row += 1
        form.addWidget(field("单位", self.f_unit), row, 0)
        form.addWidget(field("小数位数", self.f_decimals), row, 1)
        row += 1
        form.addWidget(field("最小值", self.f_min), row, 0)
        form.addWidget(field("最大值", self.f_max), row, 1)
        row += 1
        form.addWidget(field("曲线展示", self.f_curve), row, 0)
        row += 1
        form.addWidget(field("说明（可选）", self.f_desc), row, 0, 1, 2)
        row += 1

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_save = QPushButton("保存定义")
        self.btn_cancel = QPushButton("取消修改")
        self.btn_cancel.setProperty("variant", "secondary")
        self.btn_save.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addStretch()
        form.addLayout(btn_row, row, 0, 1, 4)

        card_layout.addWidget(body, 1)
        return card

    # ===== 表格刷新 =====

    def _refresh_table(self):
        """刷新表格数据（按筛选过滤）"""
        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.setRowCount(0)
        params = store.filtered_params()
        self.table.setRowCount(len(params))

        for row, p in enumerate(params):
            # checkbox（居中放在 container 里，不被裁切）
            cb_container = QWidget()
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb = QCheckBox()
            cb.stateChanged.connect(self._update_toolbar_state)
            cb_layout.addWidget(cb)
            self.table.setCellWidget(row, 0, cb_container)
            # 数据列
            # type 内部值转显示值（float32→float）
            type_val = p.get("type","")
            if type_val in TYPE_INTERNAL:
                type_val = TYPE_DISPLAY[TYPE_INTERNAL.index(type_val)]
            vals = [p.get("name",""), p.get("display",""), p.get("address",""),
                    p.get("category",""), type_val, p.get("access",""),
                    p.get("unit",""), str(p.get("decimals",0)),
                    f'{p.get("min","")} ~ {p.get("max","")}', p.get("desc","")]
            for col, val in enumerate(vals, 1):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)

        self.table.blockSignals(False)
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
        # 上移/下移：仅在勾选 1 行时启用，且不是首/末行
        single = len(checked) == 1
        total = self.table.rowCount()
        self.btn_up.setEnabled(single and checked[0] > 0)
        self.btn_down.setEnabled(single and checked[0] < total - 1)

    def _on_table_item_changed(self):
        self._update_toolbar_state()

    # ===== 筛选 =====

    def _on_filter_changed(self, text):
        store.param_filter = "all" if text == "全部" else text
        self._refresh_table()

    # ===== CRUD =====

    def _set_edit_mode(self, mode: str):
        self._edit_mode = mode
        if mode == "create":
            self._editing_name = None
            self.form_title.setText("新增参数")
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
            params = store.filtered_params()
            p = params[checked[0]]
            self._editing_name = p["name"]
            self.form_title.setText(f'编辑参数：{p["name"]}')
            self._load_form(p)

    def _clear_form(self):
        # 程序填充时屏蔽信号，避免误触发"未保存"
        for w in (self.f_name, self.f_display, self.f_address, self.f_unit,
                  self.f_decimals, self.f_min, self.f_max, self.f_desc):
            w.blockSignals(True)
        for cb in (self.f_category, self.f_type, self.f_access, self.f_curve):
            cb.blockSignals(True)
        self.f_name.clear()
        self.f_display.clear()
        self.f_address.clear()
        self.f_category.setCurrentIndex(0)
        self.f_type.setCurrentIndex(0)
        self.f_access.setCurrentIndex(0)
        self.f_curve.setCurrentIndex(1)  # 默认"否"
        self.f_unit.clear()
        self.f_decimals.setText("0")
        self.f_min.clear()
        self.f_max.clear()
        self.f_desc.clear()
        for w in (self.f_name, self.f_display, self.f_address, self.f_unit,
                  self.f_decimals, self.f_min, self.f_max, self.f_desc):
            w.blockSignals(False)
        for cb in (self.f_category, self.f_type, self.f_access, self.f_curve):
            cb.blockSignals(False)
        # 清空 = 无未保存改动
        self._set_dirty(False)

    def _load_form(self, p: dict):
        # 程序填充时屏蔽信号，避免载入即"未保存"
        for w in (self.f_name, self.f_display, self.f_address, self.f_unit,
                  self.f_decimals, self.f_min, self.f_max, self.f_desc):
            w.blockSignals(True)
        for cb in (self.f_category, self.f_type, self.f_access, self.f_curve):
            cb.blockSignals(True)
        self.f_name.setText(p.get("name", ""))
        self.f_display.setText(p.get("display", ""))
        self.f_address.setText(p.get("address", ""))
        self.f_category.setCurrentText(p.get("category", "采样参数"))
        # 内部值转显示值（float32→float）
        type_val = p.get("type", "uint16")
        type_idx = TYPE_INTERNAL.index(type_val) if type_val in TYPE_INTERNAL else 0
        self.f_type.setCurrentIndex(type_idx)
        self.f_access.setCurrentText(p.get("access", "只读"))
        self.f_curve.setCurrentText(p.get("curve", "是"))
        self.f_unit.setText(p.get("unit", ""))
        self.f_decimals.setText(str(p.get("decimals", 0)))
        self.f_min.setText(str(p.get("min", "")))
        self.f_max.setText(str(p.get("max", "")))
        self.f_desc.setText(p.get("desc", ""))
        for w in (self.f_name, self.f_display, self.f_address, self.f_unit,
                  self.f_decimals, self.f_min, self.f_max, self.f_desc):
            w.blockSignals(False)
        for cb in (self.f_category, self.f_type, self.f_access, self.f_curve):
            cb.blockSignals(False)
        # 载入刚载入 = 还未改动
        self._set_dirty(False)

    def _collect_form(self) -> dict:
        # 显示值转内部值（float→float32）
        type_display = self.f_type.currentText()
        type_idx = TYPE_DISPLAY.index(type_display) if type_display in TYPE_DISPLAY else 0
        type_internal = TYPE_INTERNAL[type_idx]
        return {
            "name": self.f_name.text().strip(),
            "display": self.f_display.text().strip(),
            "address": self.f_address.text().strip(),
            "category": self.f_category.currentText(),
            "type": type_internal,
            "access": self.f_access.currentText(),
            "curve": self.f_curve.currentText(),
            "unit": self.f_unit.text().strip(),
            "decimals": int(self.f_decimals.text() or 0),
            "min": self.f_min.text().strip(),
            "max": self.f_max.text().strip(),
            "desc": self.f_desc.text().strip(),
        }

    def _save(self):
        data = self._collect_form()
        result = store.validate_param(data, device_id=store.current_device_id, exclude_name=self._editing_name if self._edit_mode == "edit" else None)
        if not result["ok"]:
            msgs = "\n".join(f"• {k}: {v}" for k, v in result["errors"].items())
            QMessageBox.warning(self, "保存失败", "请修正以下错误：\n" + msgs)
            return

        params = store._cur_params()
        if self._edit_mode == "edit":
            # 更新现有
            for i, p in enumerate(params):
                if p["name"] == self._editing_name:
                    params[i] = data
                    break
        else:
            params.append(data)

        store.save_params()
        self._refresh_table()
        self._set_edit_mode("create")  # 内部会 _clear_form → 恢复"已同步"

    def _delete_selected(self):
        checked = self._checked_rows()
        if not checked:
            return
        params = store.filtered_params()
        names = [params[r]["name"] for r in checked]
        reply = QMessageBox.question(
            self, "删除确认",
            f"确认删除 {len(names)} 条参数：{', '.join(names)}？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            params = store._cur_params()
            store.params[store.current_device_id] = [p for p in params if p["name"] not in names]
            store.save_params()
            self._refresh_table()
            self._set_edit_mode("create")  # 清空表单 + 恢复"已同步"

    def _move_up(self):
        """上移勾选行：在当前设备参数列表中与前一项交换"""
        checked = self._checked_rows()
        if len(checked) != 1:
            return
        row = checked[0]
        params = store.filtered_params()
        if row <= 0:
            return
        name = params[row]["name"]
        prev_name = params[row - 1]["name"]
        all_params = store._cur_params()
        idx_cur = next(i for i, p in enumerate(all_params) if p["name"] == name)
        idx_prev = next(i for i, p in enumerate(all_params) if p["name"] == prev_name)
        all_params[idx_cur], all_params[idx_prev] = all_params[idx_prev], all_params[idx_cur]
        store.save_params()
        self._refresh_table()
        self._check_row(row - 1)

    def _move_down(self):
        """下移勾选行：在当前设备参数列表中与后一项交换"""
        checked = self._checked_rows()
        if len(checked) != 1:
            return
        row = checked[0]
        params = store.filtered_params()
        if row >= len(params) - 1:
            return
        name = params[row]["name"]
        next_name = params[row + 1]["name"]
        all_params = store._cur_params()
        idx_cur = next(i for i, p in enumerate(all_params) if p["name"] == name)
        idx_next = next(i for i, p in enumerate(all_params) if p["name"] == next_name)
        all_params[idx_cur], all_params[idx_next] = all_params[idx_next], all_params[idx_cur]
        store.save_params()
        self._refresh_table()
        self._check_row(row + 1)

    def _check_row(self, row: int):
        """勾选指定行（用于移动后保持选中跟随）"""
        if 0 <= row < self.table.rowCount():
            container = self.table.cellWidget(row, 0)
            if container:
                cb = container.findChild(QCheckBox)
                if cb:
                    cb.setChecked(True)

    def _cancel(self):
        self._set_edit_mode("create")

    # ===== 表单 dirty 标记 =====

    def _on_form_changed(self):
        """表单任一字段改动 → 标记未保存"""
        self._set_dirty(True)

    def _set_dirty(self, dirty: bool):
        """更新表单 dirty 状态（影响"已同步/未保存" chip）"""
        if dirty:
            self.dirty_tag.update_state("未保存", "warn")
        else:
            self.dirty_tag.update_state("已同步", "ok")
        self.dirty_changed.emit(dirty)
