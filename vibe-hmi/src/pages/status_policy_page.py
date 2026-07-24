"""
状态策略页

迁移自原型 js/pages/statusPolicy.js。
两卡并排：卡片A 离线判定策略（表单 + 说明 + 按钮）+ 卡片B 状态转换预览表。

超时值 input → 实时联动预览表的阈值文本和 tag。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QCheckBox, QLineEdit, QComboBox,
    QAbstractItemView, QHeaderView, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from .. import theme
from ..store import store


# 状态转换预览数据（4 行）
TRANSITIONS = [
    {"current": "在线", "current_color": "ok", "condition": "{t} 分钟内", "result": "在线", "result_color": "ok"},
    {"current": "在线", "current_color": "", "condition": "超过 {t} 分钟", "result": "离线", "result_color": ""},
    {"current": "告警", "current_color": "warn", "condition": "{t} 分钟内", "result": "告警", "result_color": "warn"},
    {"current": "告警", "current_color": "", "condition": "超过 {t} 分钟", "result": "离线", "result_color": ""},
]


class StatusPolicyPage(QWidget):
    """状态策略页"""

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._on_timeout_changed()  # 用实际策略值初始化说明表和预览表

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self._build_policy_card())
        row.addWidget(self._build_preview_card())
        layout.addLayout(row)
        layout.addStretch()

    def _build_policy_card(self) -> QFrame:
        """卡片A 离线判定策略"""
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        head = self._make_head("离线判定策略", "", "")
        cl.addWidget(head)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 14, 14, 14)
        bl.setSpacing(14)

        # 表单
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.cb_enable = QCheckBox("启用离线判定")
        self.cb_enable.setChecked(store.policy.get("enable", True))
        self.cb_enable.setObjectName("check-label")

        self.input_timeout = QLineEdit(str(store.policy.get("timeout", 10)))
        self.input_timeout.setFixedWidth(80)
        self.input_timeout.textChanged.connect(self._on_timeout_changed)

        self.combo_unit = QComboBox()
        self.combo_unit.addItems(["分钟", "秒"])
        self.combo_unit.setCurrentText(store.policy.get("unit", "分钟"))
        self.combo_unit.setFixedWidth(80)
        self.combo_unit.currentTextChanged.connect(self._on_timeout_changed)

        self.combo_scope = QComboBox()
        self.combo_scope.addItems(["全部设备", "仅采样设备", "自定义设备"])
        self.combo_scope.setCurrentText(store.policy.get("scope", "全部设备"))
        self.combo_scope.setFixedWidth(140)

        form.addRow("启用", self.cb_enable)
        form.addRow("无通讯超时", self.input_timeout)
        form.addRow("时间单位", self.combo_unit)
        form.addRow("作用范围", self.combo_scope)
        bl.addLayout(form)

        # 说明表（无边框键值表，超时值联动更新）
        self._rule_labels = []  # 存需要联动更新的 value QLabel
        rules = [
            ("判定依据", "最后通讯时间超过阈值", False),
            ("在线 → 离线", "超过 10 分钟 无通讯", True),
            ("告警 → 离线", "超过 10 分钟 无通讯", True),
            ("离线恢复", "收到有效响应后恢复在线", False),
        ]
        for key, val, dynamic in rules:
            r = QHBoxLayout()
            k = QLabel(key)
            k.setFixedWidth(100)
            k.setStyleSheet(f"color: {theme.HEX['MUTED']}; font-weight: {theme.FW_BOLD};")
            v = QLabel(val)
            v.setStyleSheet(f"color: {theme.HEX['TEXT']};")
            r.addWidget(k)
            r.addWidget(v, 1)
            bl.addLayout(r)
            if dynamic:
                self._rule_labels.append(v)

        bl.addSpacing(8)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_save = QPushButton("保存状态策略")
        btn_save.clicked.connect(self._save)
        btn_reset = QPushButton("恢复默认策略")
        btn_reset.setProperty("variant", "secondary")
        btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()
        bl.addLayout(btn_row)

        cl.addWidget(body, 1)
        return card

    def _build_preview_card(self) -> QFrame:
        """卡片B 状态转换预览表"""
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self.preview_tag_text = "10 分钟"
        head = self._make_head("状态转换预览", self.preview_tag_text, "warn")
        self.preview_head = head
        cl.addWidget(head)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(10, 10, 10, 10)

        cols = ["当前状态", "条件", "设备总览显示"]
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(len(cols))
        self.preview_table.setHorizontalHeaderLabels(cols)
        self.preview_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setRowCount(len(TRANSITIONS))
        self._refresh_preview()
        bl.addWidget(self.preview_table)
        cl.addWidget(body, 1)
        return card

    def _refresh_preview(self):
        """刷新预览表（用当前超时值填充 {t} 占位）"""
        t = self.input_timeout.text() or "10"
        unit = self.combo_unit.currentText()

        color_map = {
            "ok": theme.HEX["OK"],
            "warn": theme.HEX["WARN"],
            "": theme.HEX["MUTED"],
        }
        for row, tr in enumerate(TRANSITIONS):
            cur_color = QColor(color_map.get(tr["current_color"], theme.HEX["TEXT"]))
            res_color = QColor(color_map.get(tr["result_color"], theme.HEX["TEXT"]))
            condition = tr["condition"].replace("{t}", t)

            # 当前状态
            item0 = QTableWidgetItem(tr["current"])
            item0.setForeground(cur_color)
            # 条件
            item1 = QTableWidgetItem(condition)
            # 结果
            item2 = QTableWidgetItem(tr["result"])
            item2.setForeground(res_color)
            for i, item in enumerate([item0, item1, item2]):
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.preview_table.setItem(row, i, item)

        # 更新 tag
        tag_label = self.preview_head.findChild(QLabel, "")
        # 直接找 head 里的 tag QLabel
        for child in self.preview_head.children():
            if isinstance(child, QLabel) and child.objectName() == "tag":
                child.setText(f"{t} {unit}")
                break

    def _on_timeout_changed(self):
        """超时值变化 → 联动预览表、tag 和说明表"""
        self._refresh_preview()
        # 更新说明表中的动态文字
        t = self.input_timeout.text() or "10"
        unit = self.combo_unit.currentText()
        for label in self._rule_labels:
            label.setText(f"超过 {t} {unit} 无通讯")

    def _save(self):
        """保存策略到 store 并持久化"""
        try:
            timeout = int(self.input_timeout.text() or "10")
        except ValueError:
            timeout = 10
        store.update_policy(
            enable=self.cb_enable.isChecked(),
            timeout=timeout,
            unit=self.combo_unit.currentText(),
            scope=self.combo_scope.currentText(),
        )
        self._on_timeout_changed()
        QMessageBox.information(self, "保存", "状态策略已保存")

    def _reset(self):
        """恢复默认策略"""
        self.input_timeout.setText("10")
        self.combo_unit.setCurrentText("分钟")
        self.combo_scope.setCurrentText("全部设备")
        self.cb_enable.setChecked(True)
        store.update_policy(enable=True, timeout=10, unit="分钟", scope="全部设备")
        self._on_timeout_changed()

    def _make_head(self, title: str, tag_text: str, tag_variant: str) -> QFrame:
        head = QFrame()
        head.setObjectName("card-head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(10, 0, 10, 0)
        lbl = QLabel(title)
        lbl.setObjectName("card-title")
        hl.addWidget(lbl)
        hl.addStretch()
        if tag_text:
            tag = QLabel(tag_text)
            tag.setObjectName("tag")
            if tag_variant:
                tag.setProperty("variant", tag_variant)
            tag.setFixedHeight(18)
            hl.addWidget(tag, alignment=Qt.AlignmentFlag.AlignVCenter)
        return head
