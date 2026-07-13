"""
参数配置页

迁移自原型 js/pages/params.js。
左卡：参数表（QTableWidget 11 列）+ 工具栏（新增/编辑/删除/导入/导出 + 设备地址 + 分类筛选）
右卡：编辑表单（QFormLayout）+ 校验 + 保存/取消

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
from PySide6.QtCore import Qt, Signal
from .. import theme
from ..store import store


# 数据类型 / 权限 / 分类 选项
TYPES = ["uint8", "int16", "uint16", "int32", "uint32", "float32", "bool"]
ACCESSES = ["只读", "只写", "读写"]
CATEGORIES = ["采样参数", "配置参数"]

# 表格列：checkbox/参数名/显示名/地址/分类/类型/权限/单位/小数/范围/说明
COLS = ["", "参数名", "显示名", "地址", "分类", "类型", "权限", "单位", "小数", "范围", "说明"]


class ParamsPage(QWidget):
    """参数配置页"""

    def __init__(self):
        super().__init__()
        self._edit_mode = "create"  # 'create' | 'edit'
        self._editing_name = None
        self._build_ui()
        self._refresh_table()

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
        self.dirty_tag = QLabel("已同步")
        self.dirty_tag.setObjectName("tag")
        head_layout.addWidget(title)
        head_layout.addStretch()
        head_layout.addWidget(self.dirty_tag)
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
        self.btn_import = QPushButton("导入模板")
        self.btn_import.setProperty("variant", "secondary")
        self.btn_export = QPushButton("导出模板")
        self.btn_export.setProperty("variant", "secondary")

        self.btn_create.clicked.connect(lambda: self._set_edit_mode("create"))
        self.btn_edit.clicked.connect(lambda: self._set_edit_mode("edit"))
        self.btn_delete.clicked.connect(self._delete_selected)

        toolbar.addWidget(self.btn_create)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_import)
        toolbar.addWidget(self.btn_export)
        toolbar.addStretch()

        # 设备地址
        toolbar.addWidget(QLabel("设备地址"))
        self.slave_input = NoWheelSpinBox()
        self.slave_input.setRange(1, 247)
        self.slave_input.setValue(store.slave_id)
        self.slave_input.setFixedWidth(70)
        self.slave_input.valueChanged.connect(self._on_slave_changed)
        toolbar.addWidget(self.slave_input)

        # 分类筛选
        toolbar.addWidget(QLabel("分类筛选"))
        self.filter_combo = NoWheelComboBox()
        self.filter_combo.addItems(["全部", "采样参数", "配置参数"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.filter_combo)

        body_layout.addLayout(toolbar)

        # 参数表（固定高度，行多了内部滚动）
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 34)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemChanged.connect(self._on_table_item_changed)
        # 固定高度（约 8 行可见 + 表头），超出滚动
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
        form_tag = QLabel("表单")
        form_tag.setObjectName("tag")
        head_layout.addWidget(self.form_title)
        head_layout.addStretch()
        head_layout.addWidget(form_tag)
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
        self.f_type.addItems(TYPES)
        self.f_access = NoWheelComboBox()
        self.f_access.addItems(ACCESSES)
        self.f_unit = QLineEdit()
        self.f_decimals = NoWheelSpinBox()
        self.f_decimals.setRange(0, 10)
        self.f_min = QLineEdit()
        self.f_max = QLineEdit()
        self.f_desc = QLineEdit()

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
        form.addWidget(field("说明（可选）", self.f_desc), row, 0, 1, 2)
        row += 1

        # 按钮
        btn_row = QHBoxLayout()
        self.btn_save = QPushButton("保存定义")
        self.btn_validate = QPushButton("校验定义")
        self.btn_validate.setProperty("variant", "secondary")
        self.btn_cancel = QPushButton("取消修改")
        self.btn_cancel.setProperty("variant", "secondary")
        self.btn_save.clicked.connect(self._save)
        self.btn_validate.clicked.connect(self._validate)
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_validate)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addStretch()
        form.addLayout(btn_row, row, 0, 1, 4)

        card_layout.addWidget(body, 1)
        return card

    # ===== 表格刷新 =====

    def _refresh_table(self):
        """刷新表格数据（按筛选过滤）"""
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        params = store.filtered_params()
        self.table.setRowCount(len(params))

        for row, p in enumerate(params):
            # checkbox
            cb = QCheckBox()
            cb.setStyleSheet("margin-left:10px;")
            self.table.setCellWidget(row, 0, cb)
            # 数据列
            vals = [p.get("name",""), p.get("display",""), p.get("address",""),
                    p.get("category",""), p.get("type",""), p.get("access",""),
                    p.get("unit",""), str(p.get("decimals",0)),
                    f'{p.get("min","")} ~ {p.get("max","")}', p.get("desc","")]
            for col, val in enumerate(vals, 1):
                item = QTableWidgetItem(str(val))
                self.table.setItem(row, col, item)

        self.table.blockSignals(False)
        self._update_toolbar_state()

    # ===== 工具栏状态 =====

    def _checked_rows(self) -> list[int]:
        """获取勾选的行号"""
        rows = []
        for row in range(self.table.rowCount()):
            cb = self.table.cellWidget(row, 0)
            if cb and cb.isChecked():
                rows.append(row)
        return rows

    def _update_toolbar_state(self):
        checked = self._checked_rows()
        self.btn_edit.setEnabled(len(checked) == 1)
        self.btn_delete.setEnabled(len(checked) >= 1)

    def _on_table_item_changed(self):
        self._update_toolbar_state()

    # ===== 筛选 / 设备地址 =====

    def _on_filter_changed(self, text):
        store.param_filter = "all" if text == "全部" else text
        self._refresh_table()

    def _on_slave_changed(self, value):
        store.slave_id = value

    # ===== CRUD =====

    def _set_edit_mode(self, mode: str):
        self._edit_mode = mode
        if mode == "create":
            self._editing_name = None
            self.form_title.setText("新增参数")
            self._clear_form()
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
        self.f_name.clear()
        self.f_display.clear()
        self.f_address.clear()
        self.f_category.setCurrentIndex(0)
        self.f_type.setCurrentIndex(0)
        self.f_access.setCurrentIndex(0)
        self.f_unit.clear()
        self.f_decimals.setValue(0)
        self.f_min.clear()
        self.f_max.clear()
        self.f_desc.clear()

    def _load_form(self, p: dict):
        self.f_name.setText(p.get("name", ""))
        self.f_display.setText(p.get("display", ""))
        self.f_address.setText(p.get("address", ""))
        self.f_category.setCurrentText(p.get("category", "采样参数"))
        self.f_type.setCurrentText(p.get("type", "uint16"))
        self.f_access.setCurrentText(p.get("access", "只读"))
        self.f_unit.setText(p.get("unit", ""))
        self.f_decimals.setValue(int(p.get("decimals", 0)))
        self.f_min.setText(str(p.get("min", "")))
        self.f_max.setText(str(p.get("max", "")))
        self.f_desc.setText(p.get("desc", ""))

    def _collect_form(self) -> dict:
        return {
            "name": self.f_name.text().strip(),
            "display": self.f_display.text().strip(),
            "address": self.f_address.text().strip(),
            "category": self.f_category.currentText(),
            "type": self.f_type.currentText(),
            "access": self.f_access.currentText(),
            "unit": self.f_unit.text().strip(),
            "decimals": self.f_decimals.value(),
            "min": self.f_min.text().strip(),
            "max": self.f_max.text().strip(),
            "desc": self.f_desc.text().strip(),
        }

    def _validate(self):
        data = self._collect_form()
        result = store.validate_param(data, exclude_name=self._editing_name if self._edit_mode == "edit" else None)
        if result["ok"]:
            QMessageBox.information(self, "校验", "校验通过")
        else:
            msgs = "\n".join(f"• {k}: {v}" for k, v in result["errors"].items())
            QMessageBox.warning(self, "校验失败", msgs)

    def _save(self):
        data = self._collect_form()
        result = store.validate_param(data, exclude_name=self._editing_name if self._edit_mode == "edit" else None)
        if not result["ok"]:
            msgs = "\n".join(f"• {k}: {v}" for k, v in result["errors"].items())
            QMessageBox.warning(self, "保存失败", "请修正以下错误：\n" + msgs)
            return

        if self._edit_mode == "edit":
            # 更新现有
            for i, p in enumerate(store.params):
                if p["name"] == self._editing_name:
                    store.params[i] = data
                    break
        else:
            store.params.append(data)

        store.params_dirty = True
        store.save_params()
        self._update_dirty_tag()
        self._refresh_table()
        self._set_edit_mode("create")

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
            store.params = [p for p in store.params if p["name"] not in names]
            store.params_dirty = True
            store.save_params()
            self._update_dirty_tag()
            self._refresh_table()

    def _cancel(self):
        self._set_edit_mode("create")

    def _update_dirty_tag(self):
        if store.params_dirty:
            self.dirty_tag.setText("未保存")
            self.dirty_tag.setProperty("variant", "warn")
        else:
            self.dirty_tag.setText("已同步")
            self.dirty_tag.setProperty("variant", "")
        self.dirty_tag.style().polish(self.dirty_tag)
