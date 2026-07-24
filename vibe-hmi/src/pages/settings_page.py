"""
系统设置页

迁移自原型 js/pages/settings.js。
两卡并排：卡片A 软件信息（键值表）+ 卡片B 维护操作（键值表 + 按钮）。

清理日志二次确认，导出诊断 loading 动画。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from datetime import datetime

from .. import theme


class SettingsPage(QWidget):
    """系统设置页"""

    def __init__(self):
        super().__init__()
        self._start_time = datetime.now()
        self._uptime_label: QLabel | None = None
        self._build_ui()
        # 运行时长定时刷新
        self._uptime_timer = QTimer()
        self._uptime_timer.timeout.connect(self._refresh_uptime)
        self._uptime_timer.start(1000)

    def _refresh_uptime(self):
        """刷新运行时长"""
        if self._uptime_label:
            delta = datetime.now() - self._start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            mins, secs = divmod(remainder, 60)
            self._uptime_label.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self._build_info_card())
        row.addWidget(self._build_maint_card())
        layout.addLayout(row)
        layout.addStretch()

    def _build_info_card(self) -> QFrame:
        """卡片A 软件信息"""
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        cl.addWidget(self._make_head("软件信息", "正常", "ok"))

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 14, 14, 14)
        bl.setSpacing(10)

        info = [
            ("软件名称", "multi-protocol-hmi"),
            ("应用版本", "v0.1.0"),
            ("运行平台", "Windows 10/11"),
        ]
        for key, val in info:
            layout, _ = self._make_kv_row(key, val)
            bl.addLayout(layout)
        # 运行时长（动态刷新）
        uptime_layout, self._uptime_label = self._make_kv_row("运行时长", "00:00:00")
        bl.addLayout(uptime_layout)

        cl.addWidget(body, 1)
        return card

    def _build_maint_card(self) -> QFrame:
        """卡片B 维护操作"""
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        cl.addWidget(self._make_head("维护操作", "诊断", ""))

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 14, 14, 14)
        bl.setSpacing(10)

        info = [
            ("数据保存路径", "./save"),
            ("日志空间", "128 / 512 MB"),
            ("配置文件", "config.example.json"),
            ("帧错误计数", "1"),
        ]
        for key, val in info:
            layout, _ = self._make_kv_row(key, val)
            bl.addLayout(layout)

        bl.addSpacing(8)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_clean = QPushButton("清理日志")
        self.btn_clean.setProperty("variant", "secondary")
        self.btn_clean.clicked.connect(self._clean_log)
        self.btn_export = QPushButton("导出诊断")
        self.btn_export.clicked.connect(self._export_diag)
        btn_row.addWidget(self.btn_clean)
        btn_row.addWidget(self.btn_export)
        btn_row.addStretch()
        bl.addLayout(btn_row)

        cl.addWidget(body, 1)
        return card

    # ===== 操作 =====

    def _clean_log(self):
        """清理日志（二次确认）"""
        reply = QMessageBox.question(
            self, "清理日志",
            "确认清理日志？\n（默认保留最近 7 天的日志）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "清理完成", "日志已清理（保留最近 7 天）")

    def _export_diag(self):
        """导出诊断（loading 动画 → 完成提示）"""
        self.btn_export.setText("导出中...")
        self.btn_export.setEnabled(False)
        # 模拟打包延迟
        QTimer.singleShot(1000, self._export_done)

    def _export_done(self):
        self.btn_export.setText("导出诊断")
        self.btn_export.setEnabled(True)
        QMessageBox.information(
            self, "导出完成",
            "已打包运行日志、配置文件和通信统计\n保存到 ./save/diag.zip"
        )

    # ===== 辅助 =====

    def _make_kv_row(self, key: str, val: str):
        """返回 (QHBoxLayout, value QLabel)，value QLabel 供后续刷新"""
        r = QHBoxLayout()
        k = QLabel(key)
        k.setFixedWidth(100)
        k.setStyleSheet(f"color: {theme.HEX['MUTED']}; font-weight: {theme.FW_BOLD};")
        v = QLabel(val)
        v.setStyleSheet(f"color: {theme.HEX['TEXT']};")
        r.addWidget(k)
        r.addWidget(v, 1)
        return r, v

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
