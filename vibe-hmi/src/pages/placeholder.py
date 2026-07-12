"""
占位页

票02 阶段所有 10 个页面用此占位 widget。后续票逐个替换为真实实现。
（如 params → src/pages/params_page.py，替换注册表里的工厂函数）
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from .. import theme


class PlaceholderPage(QWidget):
    """页面占位：显示页面名 + "待实现"提示"""

    def __init__(self, page_name: str, ticket: str = ""):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(page_name)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: {theme.FS_XL}pt; font-weight: {theme.FW_BLACK}; color: {theme.HEX['TEXT']};")

        hint = QLabel(f"待实现{(' · ' + ticket) if ticket else ''}")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"font-size: {theme.FS_LG}pt; color: {theme.HEX['MUTED']};")

        layout.addWidget(title)
        layout.addWidget(hint)
