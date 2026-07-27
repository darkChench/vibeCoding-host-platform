"""
模型配置页

管理 LLM 提供商（provider/base_url/api_key/model/enabled）。
布局：上卡提供商列表（CRUD）+ 下卡编辑表单，参考参数配置页。
持久化到 config/model_config.json。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QGridLayout, QLineEdit,
    QComboBox, QCheckBox, QMessageBox, QAbstractItemView, QHeaderView,
    QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QWheelEvent

from .. import theme
from ..store import store

# 预设提供商
PROVIDER_PRESETS = [
    {"provider": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    {"provider": "通义千问", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    {"provider": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    {"provider": "智谱GLM", "base_url": "https://open.bigmodel.cn/api/anthropic", "model": "glm-4.6"},
    {"provider": "Moonshot", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
]

COLS = ["", "提供商", "Base URL", "模型", "API Key", "启用"]


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class StatusChip(QFrame):
    def __init__(self, text: str, variant: str = ""):
        super().__init__()
        self.setObjectName("status-chip")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(26)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(6)
        colors = {"ok": theme.HEX["OK"], "warn": theme.HEX["WARN"], "": theme.HEX["MUTED"]}
        bgs = {"ok": theme.HEX["TAG_OK_BG"], "warn": theme.HEX["TAG_WARN_BG"], "": theme.HEX["TAG_BG"]}
        color = colors.get(variant, theme.HEX["MUTED"])
        bg = bgs.get(variant, theme.HEX["TAG_BG"])
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background: {color}; border-radius: 4px; border: none;")
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-size: {theme.FS_SM}pt; font-weight: {theme.FW_BOLD}; border: none; background: transparent;")
        lay.addWidget(dot)
        lay.addWidget(lbl)
        self.setStyleSheet(f"#status-chip {{ border: 1px solid {bg}; border-radius: 13px; background: {bg}; }}")


class ModelConfigPage(QWidget):
    """模型配置页"""
    # 模型配置变化信号（供状态栏 AI 状态联动）
    config_changed = Signal()

    def __init__(self):
        super().__init__()
        self._edit_mode = "create"
        self._editing_id = None
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self._build_list_card())
        layout.addWidget(self._build_form_card())
        layout.addStretch()
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ===== 上卡：提供商列表 =====

    def _build_list_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        head = QFrame()
        head.setObjectName("card-head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(10, 0, 10, 0)
        title = QLabel("模型提供商")
        title.setObjectName("card-title")
        self.config_tag = StatusChip("未配置", "warn")
        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(self.config_tag, alignment=Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(head)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(10, 10, 10, 10)
        bl.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.btn_create = QPushButton("新增提供商")
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

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        col_widths = [40, 100, 250, 120, 150, 50]
        for i, w in enumerate(col_widths):
            self.table.setColumnWidth(i, w)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(180)
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
        self.form_title = QLabel("新增提供商")
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

        self.f_provider = NoWheelComboBox()
        for p in PROVIDER_PRESETS:
            self.f_provider.addItem(p["provider"])
        self.f_provider.addItem("自定义")
        self.f_provider.currentTextChanged.connect(self._on_provider_changed)

        self.f_base_url = QLineEdit()
        self.f_base_url.setPlaceholderText("https://...")
        self.f_api_key = QLineEdit()
        self.f_api_key.setPlaceholderText("sk-...")
        self.f_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_model = QLineEdit()
        self.f_model.setPlaceholderText("如 gpt-4o-mini")
        self.cb_enabled = QCheckBox("启用（AI 助手默认使用第一个启用的提供商）")
        self.cb_enabled.setObjectName("check-label")

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

        r = 0
        form.addWidget(field("提供商", self.f_provider), r, 0)
        form.addWidget(field("模型", self.f_model), r, 1)
        r += 1
        form.addWidget(field("Base URL", self.f_base_url), r, 0)
        form.addWidget(field("API Key", self.f_api_key), r, 1)
        r += 1
        form.addWidget(self.cb_enabled, r, 0, 1, 2)
        r += 1

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_save = QPushButton("保存")
        self.btn_test = QPushButton("测试连接")
        self.btn_test.setProperty("variant", "secondary")
        self.btn_cancel = QPushButton("取消修改")
        self.btn_cancel.setProperty("variant", "secondary")
        self.btn_save.clicked.connect(self._save)
        self.btn_test.clicked.connect(self._test_connection)
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_test)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addStretch()
        form.addLayout(btn_row, r, 0, 1, 4)

        cl.addWidget(body, 1)
        return card

    # ===== 预设联动 =====

    def _on_provider_changed(self, provider_name: str):
        """选预设时自动填充 base_url + model"""
        for p in PROVIDER_PRESETS:
            if p["provider"] == provider_name:
                self.f_base_url.setText(p["base_url"])
                self.f_model.setText(p["model"])
                return

    # ===== 表格刷新 =====

    def _refresh_table(self):
        self.table.clearContents()
        self.table.setRowCount(0)
        self.table.setRowCount(len(store.model_config))
        for row, cfg in enumerate(store.model_config):
            cb_container = QWidget()
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb = QCheckBox()
            cb.stateChanged.connect(self._update_toolbar_state)
            cb_layout.addWidget(cb)
            self.table.setCellWidget(row, 0, cb_container)

            api_key = cfg.get("api_key", "")
            masked = f"••••{api_key[-4:]}" if len(api_key) > 4 else "••••"
            vals = [cfg.get("provider", ""), cfg.get("base_url", ""),
                    cfg.get("model", ""), masked,
                    "✓" if cfg.get("enabled") else "—"]
            for col, val in enumerate(vals, 1):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, item)

        # 更新配置状态 tag（更新现有 tag 而非创建新的）
        active = store.active_model_config()
        if active:
            self._update_config_tag(f"{active['provider']} · {active['model']}", "ok")
        else:
            self._update_config_tag("未配置", "warn")
        self._update_toolbar_state()

    def _update_config_tag(self, text: str, variant: str):
        """更新现有 config_tag 的内容和颜色"""
        colors = {"ok": theme.HEX["OK"], "warn": theme.HEX["WARN"], "": theme.HEX["MUTED"]}
        bgs = {"ok": theme.HEX["TAG_OK_BG"], "warn": theme.HEX["TAG_WARN_BG"], "": theme.HEX["TAG_BG"]}
        color = colors.get(variant, theme.HEX["MUTED"])
        bg = bgs.get(variant, theme.HEX["TAG_BG"])
        # 更新 dot 和 text
        children = self.config_tag.findChildren(QLabel)
        if len(children) >= 2:
            children[0].setStyleSheet(f"background: {color}; border-radius: 4px; border: none;")
            children[1].setText(text)
            children[1].setStyleSheet(f"color: {color}; font-size: {theme.FS_SM}pt; font-weight: {theme.FW_BOLD}; border: none; background: transparent;")
        self.config_tag.setStyleSheet(f"#status-chip {{ border: 1px solid {bg}; border-radius: 13px; background: {bg}; }}")

    def _update_toolbar_state(self):
        checked = self._checked_rows()
        self.btn_edit.setEnabled(len(checked) == 1)
        self.btn_delete.setEnabled(len(checked) >= 1)

    def _checked_rows(self) -> list[int]:
        rows = []
        for row in range(self.table.rowCount()):
            container = self.table.cellWidget(row, 0)
            if container:
                cb = container.findChild(QCheckBox)
                if cb and cb.isChecked():
                    rows.append(row)
        return rows

    # ===== CRUD =====

    def _set_edit_mode(self, mode: str):
        self._edit_mode = mode
        if mode == "create":
            self._editing_id = None
            self.form_title.setText("新增提供商")
            self._clear_form()
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
            cfg = store.model_config[checked[0]]
            self._editing_id = cfg["id"]
            self.form_title.setText(f'编辑：{cfg["provider"]}')
            self._load_form(cfg)

    def _clear_form(self):
        self.f_provider.setCurrentIndex(0)
        self.f_base_url.clear()
        self.f_api_key.clear()
        self.f_model.clear()
        self.cb_enabled.setChecked(False)

    def _load_form(self, cfg: dict):
        self.f_provider.setCurrentText(cfg.get("provider", ""))
        self.f_base_url.setText(cfg.get("base_url", ""))
        self.f_api_key.setText(cfg.get("api_key", ""))
        self.f_model.setText(cfg.get("model", ""))
        self.cb_enabled.setChecked(cfg.get("enabled", False))

    def _save(self):
        provider = self.f_provider.currentText()
        base_url = self.f_base_url.text().strip()
        api_key = self.f_api_key.text().strip()
        model = self.f_model.text().strip()

        if not base_url or not base_url.startswith("http"):
            QMessageBox.warning(self, "校验失败", "Base URL 必须以 http:// 或 https:// 开头")
            return
        if not api_key:
            QMessageBox.warning(self, "校验失败", "API Key 不能为空")
            return
        if not model:
            QMessageBox.warning(self, "校验失败", "模型不能为空")
            return

        enabled = self.cb_enabled.isChecked()
        # 如果启用，取消其他配置的 enabled
        if enabled:
            for cfg in store.model_config:
                cfg["enabled"] = False

        if self._edit_mode == "edit" and self._editing_id:
            store.update_model_config(self._editing_id, provider, base_url, api_key, model, enabled)
        else:
            store.add_model_config(provider, base_url, api_key, model, enabled)

        self._refresh_table()
        self._set_edit_mode("create")
        self.config_changed.emit()

    def _delete_selected(self):
        checked = self._checked_rows()
        if not checked:
            return
        ids = [store.model_config[r]["id"] for r in checked]
        reply = QMessageBox.question(self, "删除确认", f"确认删除 {len(ids)} 个提供商配置？")
        if reply == QMessageBox.StandardButton.Yes:
            for cid in ids:
                store.delete_model_config(cid)
            self._refresh_table()
            self._set_edit_mode("create")
            self.config_changed.emit()

    def _cancel(self):
        self._set_edit_mode("create")

    def _test_connection(self):
        """测试 LLM 连接"""
        provider = self.f_provider.currentText()
        base_url = self.f_base_url.text().strip()
        api_key = self.f_api_key.text().strip()
        model = self.f_model.text().strip()

        if not base_url or not api_key or not model:
            QMessageBox.warning(self, "测试失败", "请先填写 Base URL、API Key 和模型")
            return

        self.btn_test.setText("测试中...")
        self.btn_test.setEnabled(False)

        from ..ai.llm_client import LLMClient

        try:
            client = LLMClient(base_url, api_key, model)
            # 用统一的 chat 接口测试（自动识别 OpenAI / Anthropic）
            data = client.chat([{"role": "user", "content": "你好"}])
            reply = data["choices"][0]["message"].get("content", "")
            QMessageBox.information(self, "连接成功", f"模型 {model} 连接正常\n回复：{reply}")
        except Exception as e:
            # 尝试提取 HTTP 错误详情
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                status = e.response.status_code
                body = e.response.text[:500]
                error_msg = f"HTTP {status}\n{body}"
            QMessageBox.warning(self, "连接失败", error_msg[:500])
        finally:
            self.btn_test.setText("测试连接")
            self.btn_test.setEnabled(True)
