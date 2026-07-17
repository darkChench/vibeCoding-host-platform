"""
全局 QSS 样式生成

迁移自原型 assets/hmi/css/widgets.css 的核心控件样式。
QSS 不支持 CSS 变量，色值从 theme.py 的 HEX 字典读取后拼接成 QSS 字符串。

用法：在 app.py 里读 theme.py 颜色 → 调 build_qss() → app.setStyleSheet()
"""
from . import theme


def build_qss() -> str:
    """生成全局 QSS 字符串"""
    import os
    # 箭头 SVG 的绝对路径（相对本文件定位）
    arrow_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons", "arrow-down.svg")
    arrow_path = arrow_path.replace("\\", "/")  # QSS 用正斜杠

    c = theme.HEX
    r = {
        "xs": theme.RADIUS_XS,
        "sm": theme.RADIUS_SM,
        "md": theme.RADIUS_MD,
        "lg": theme.RADIUS_LG,
        "pill": theme.RADIUS_PILL,
    }

    return f"""
    /* ===== 全局 ===== */
    QWidget {{
        font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
        font-size: {theme.FS_MD}pt;
        color: {c["TEXT"]};
    }}
    QScrollArea {{
        background: #ffffff;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background: #ffffff;
    }}

    /* ===== 滚动条 ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical,
    QScrollBar::handle:horizontal {{
        background: #a8b0bb;
        border-radius: 4px;
        min-height: 30px;
        min-width: 30px;
    }}
    QScrollBar::handle:vertical:hover,
    QScrollBar::handle:horizontal:hover {{
        background: #8a93a0;
    }}
    QScrollBar::handle:vertical:pressed,
    QScrollBar::handle:horizontal:pressed {{
        background: #6c7682;
    }}
    QScrollBar::add-line,
    QScrollBar::sub-line {{
        background: none;
        border: none;
        height: 0px;
        width: 0px;
    }}
    QScrollBar::add-page,
    QScrollBar::sub-page {{
        background: transparent;
    }}

    /* ===== 原生菜单栏 ===== */
    QMenuBar {{
        background: {c["MENUBAR_BG"]};
        color: {c["MENUBAR_FG"]};
        font-size: {theme.FS_MD}pt;
        font-weight: {theme.FW_REGULAR};
        padding: 2px;
    }}
    QMenuBar::item {{
        padding: 4px 10px;
        background: transparent;
        border-radius: {r["xs"]}px;
    }}
    QMenuBar::item:selected {{
        background: #ffffff;
        border: 1px solid {c["LINE"]};
    }}

    /* ===== 工具栏（自定义 QFrame） ===== */
    QFrame#toolbar {{
        background: {c["CHROME"]};
        border-bottom: 1px solid {c["LINE"]};
    }}
    QLabel#tool-label {{
        color: {c["MUTED"]};
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_BOLD};
    }}
    QLabel#stats-strip {{
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_BOLD};
    }}
    QLabel#stat-ok {{
        color: {c["OK"]};
    }}
    QLabel#stat-warn {{
        color: {c["WARN"]};
    }}

    /* ===== 按钮 ===== */
    QPushButton {{
        min-height: {theme.CONTROL_H}px;
        padding: 0 11px;
        border: 1px solid {c["PRIMARY_DARK"]};
        border-radius: {r["sm"]}px;
        background: {c["PRIMARY"]};
        color: #ffffff;
        font-size: {theme.FS_MD}pt;
        font-weight: {theme.FW_BOLD};
    }}
    QPushButton:hover {{
        background: {c["PRIMARY_DARK"]};
    }}
    QPushButton[variant="secondary"] {{
        border-color: {c["LINE_DARK"]};
        background: #ffffff;
        color: {c["TEXT"]};
    }}
    QPushButton[variant="secondary"]:hover {{
        background: #eef3f8;
    }}
    QPushButton:disabled {{
        border-color: {c["DISABLED_BORDER"]};
        background: {c["DISABLED_BG"]};
        color: {c["DISABLED_FG"]};
    }}

    /* ===== 输入框 / 下拉框 ===== */
    QLineEdit {{
        min-height: {theme.CONTROL_H}px;
        padding: 0 9px;
        border: 1px solid {c["LINE_DARK"]};
        border-radius: {r["sm"]}px;
        background: #ffffff;
        color: {c["TEXT"]};
        font-size: {theme.FS_MD}pt;
        font-weight: {theme.FW_BOLD};
    }}
    QLineEdit:focus {{
        border-color: {c["PRIMARY"]};
    }}
    /* QComboBox：保留边框/圆角/focus，箭头用系统原生（不设 drop-down/down-arrow） */
    QComboBox {{
        min-height: {theme.CONTROL_H}px;
        padding: 0 9px;
        border: 1px solid {c["LINE_DARK"]};
        border-radius: {r["sm"]}px;
        background: #ffffff;
        color: {c["TEXT"]};
        font-size: {theme.FS_MD}pt;
        font-weight: {theme.FW_BOLD};
    }}
    QComboBox:focus {{
        border-color: {c["PRIMARY"]};
    }}
    QComboBox:hover {{
        border-color: {c["PRIMARY"]};
    }}
    /* 下拉箭头（本地 SVG 文件） */
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: url({arrow_path});
        width: 12px;
        height: 8px;
    }}
    /* 下拉弹窗（不设 border-radius/padding，避免弹出时抖动） */
    QComboBox QAbstractItemView {{
        border: 1px solid {c["LINE_DARK"]};
        background: #ffffff;
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 28px;
        padding: 0 10px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background: {c["SELECT_BG"]};
        color: {c["PRIMARY"]};
    }}
    QComboBox QAbstractItemView::item:selected {{
        background: {c["SELECT_BG"]};
        color: {c["PRIMARY"]};
        font-weight: {theme.FW_BOLD};
    }}
    QLineEdit:focus {{
        border-color: {c["PRIMARY"]};
    }}

    /* ===== 原生状态栏 ===== */
    QStatusBar {{
        background: {c["STATUSBAR_BG"]};
        color: {c["STATUSBAR_FG"]};
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_REGULAR};
        border-top: 1px solid {c["LINE_DARK"]};
    }}
    QStatusBar QLabel {{
        color: {c["STATUSBAR_FG"]};
        font-size: {theme.FS_SM}pt;
    }}

    /* ===== 工作区 ===== */
    #workspace {{
        background: {c["WORKSPACE_BG"]};
    }}

    /* ===== 卡片 ===== */
    QFrame#card {{
        border: 1px solid {c["LINE"]};
        border-radius: {r["md"]}px;
        background: #ffffff;
    }}
    QFrame#card-head {{
        min-height: 36px;
        background: #f7f9fc;
        border-bottom: 1px solid {c["LINE"]};
        font-weight: {theme.FW_BOLD};
    }}
    QLabel#card-title {{
        font-size: {theme.FS_LG}pt;
        font-weight: {theme.FW_BLACK};
    }}

    /* ===== 表格 ===== */
    QTableWidget {{
        border: 1px solid {c["LINE"]};
        border-radius: {r["md"]}px;
        background: #ffffff;
        gridline-color: transparent;
        font-size: {theme.FS_MD}pt;
    }}
    QTableWidget::item {{
        border-bottom: 1px solid {c["LINE"]};
        outline: none;
    }}
    QTableWidget::item:hover {{
        background: {c["ROW_HOVER_BG"]};
    }}
    QTableWidget::item:selected {{
        background: {c["SELECT_BG"]};
        color: {c["PRIMARY_DARK"]};
    }}
    QHeaderView::section {{
        background: {c["TH_BG"]};
        color: {c["TH_FG"]};
        font-weight: {theme.FW_BOLD};
        padding: 6px 4px;
        border: none;
        border-bottom: 1px solid {c["LINE"]};
    }}

    /* ===== 标签 tag ===== */
    QLabel#tag {{
        border-radius: 10px;
        padding: 2px 8px;
        min-height: 14px;
        background: {c["TAG_BG"]};
        color: {c["TAG_FG"]};
        font-size: {theme.FS_XS}pt;
        font-weight: {theme.FW_BOLD};
    }}
    QLabel#tag[variant="warn"] {{
        background: {c["TAG_WARN_BG"]};
        color: {c["WARN"]};
    }}
    QLabel#tag[variant="ok"] {{
        background: {c["TAG_OK_BG"]};
        color: {c["OK"]};
    }}

    /* ===== 表单 label ===== */
    QLabel {{
        background: transparent;
    }}

    /* ===== 侧边栏 ===== */
    #sidebar {{
        background: {c["SIDEBAR_BG"]};
        border-right: 1px solid {c["LINE"]};
    }}
    QLabel#pane-title {{
        background: {c["PANE_TITLE_BG"]};
        color: {c["TEXT"]};
        font-weight: {theme.FW_BOLD};
        font-size: {theme.FS_MD}pt;
        padding: 0 12px;
        min-height: 38px;
        max-height: 38px;
        border-bottom: 1px solid {c["LINE"]};
    }}
    QWidget#tree QLabel#tree-heading {{
        color: {c["MUTED"]};
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_BOLD};
        padding: 0 8px;
    }}
    QFrame#tree-item {{
        min-height: {theme.CONTROL_H}px;
        border: 1px solid transparent;
        border-radius: {r["sm"]}px;
        background: transparent;
    }}
    QFrame#tree-item[hovered="true"] {{
        border-color: {c["LINE"]};
        background: #ffffff;
    }}
    QFrame#tree-item[active="true"] {{
        border-color: {c["SELECT_BORDER_TREE"]};
        background: {c["SELECT_BG"]};
    }}
    QLabel#tree-icon {{
        color: {c["MUTED"]};
        font-size: {theme.FS_MD}pt;
    }}
    QFrame#tree-item[active="true"] QLabel#tree-icon {{
        color: {c["PRIMARY"]};
    }}
    QLabel#tree-name {{
        color: {c["TEXT"]};
        font-size: {theme.FS_MD}pt;
        font-weight: {theme.FW_REGULAR};
    }}
    QFrame#tree-item[active="true"] QLabel#tree-name {{
        color: {c["PRIMARY"]};
        font-weight: {theme.FW_BOLD};
    }}
    QLabel#tree-tag {{
        border-radius: 10px;
        padding: 3px 8px;
        min-height: 16px;
        background: {c["TAG_BG"]};
        color: {c["TAG_FG"]};
        font-size: {theme.FS_XS}pt;
        font-weight: {theme.FW_BOLD};
    }}
    QLabel#tree-tag[variant="ok"] {{
        background: {c["TAG_OK_BG"]};
        color: {c["OK"]};
    }}
    QLabel#tree-tag[variant="warn"] {{
        background: {c["TAG_WARN_BG"]};
        color: {c["WARN"]};
    }}

    /* ===== 主区 tabs ===== */
    #main-area {{
        background: #ffffff;
        border-right: 1px solid {c["LINE"]};
    }}
    #main-area QStackedWidget {{
        background: #ffffff;
    }}
    #main-area QStackedWidget > * {{
        background: #ffffff;
    }}
    QScrollArea#tabs-scroll {{
        background: #f7f9fc;
        border-bottom: 1px solid {c["LINE"]};
        border: none;
    }}
    QWidget#tabs {{
        background: transparent;
    }}
    QPushButton#tab {{
        min-height: {theme.CONTROL_H}px;
        padding: 0 12px;
        border: 1px solid {c["LINE"]};
        border-bottom: none;
        border-top-left-radius: {r["md"]}px;
        border-top-right-radius: {r["md"]}px;
        background: {c["CHROME"]};
        color: #35465a;
        font-size: {theme.FS_MD}pt;
        font-weight: {theme.FW_BOLD};
    }}
    QPushButton#tab:checked {{
        background: #ffffff;
        color: {c["PRIMARY"]};
        border-color: {c["SELECT_BORDER_TAB"]};
    }}

    /* ===== 监控页 ===== */
    QFrame#metric {{
        border: 1px solid {c["LINE"]};
        border-radius: {r["md"]}px;
        background: #f8fafc;
    }}
    QLabel#metric-label {{
        color: {c["MUTED"]};
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_BOLD};
    }}
    QLabel#metric-value {{
        font-size: {theme.FS_XL}pt;
        font-weight: {theme.FW_BLACK};
    }}
    QFrame#curve-chip {{
        border: 1px solid {c["LINE"]};
        border-radius: 13px;
        background: #f8fafc;
    }}
    QFrame#status-chip {{
        border: 1px solid {c["TAG_OK_BG"]};
        border-radius: 13px;
        background: {c["TAG_OK_BG"]};
    }}
    QFrame#curve-chip[hidden="true"] {{
        border-style: dashed;
        border-color: {c["LINE"]};
        background: #f1f5f9;
    }}
    QFrame#curve-chip:hover {{
        border-color: {c["PRIMARY"]};
        background: {c["SELECT_BG"]};
    }}
    QLabel#chip-text {{
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_BOLD};
        background: transparent;
        border: none;
    }}
    QLabel#empty-state {{
        color: {c["MUTED"]};
        font-size: {theme.FS_MD}pt;
        font-weight: {theme.FW_BOLD};
    }}

    /* ===== 串口控制台 ===== */
    QFrame#console {{
        border: 1px solid {c["LINE"]};
        border-radius: {r["md"]}px;
        background: #ffffff;
    }}
    QFrame#console-tabs {{
        min-height: 38px;
        background: #f7f9fc;
        border-bottom: 1px solid {c["LINE"]};
    }}
    QPushButton#console-tab {{
        min-height: 28px;
        padding: 0 9px;
        border: 1px solid {c["LINE"]};
        border-radius: {r["sm"]}px;
        background: #ffffff;
        color: #344457;
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_BOLD};
    }}
    QPushButton#console-tab[active="true"] {{
        border-color: {c["PRIMARY"]};
        background: {c["SELECT_BG"]};
        color: {c["PRIMARY"]};
    }}
    QPlainTextEdit#terminal {{
        background: #ffffff;
        color: #17202c;
        border: none;
        font-family: Consolas, "Courier New", monospace;
        font-size: {theme.FS_SM}pt;
        padding: 8px 10px;
    }}
    QFrame#sendbar {{
        min-height: 42px;
        background: #f7f9fc;
        border-top: 1px solid {c["LINE"]};
    }}
    QLineEdit#send-input {{
        min-height: 28px;
    }}
    QPushButton#btn-send {{
        min-height: 28px;
    }}
    /* 发送历史浮层 */
    QFrame#history-popover {{
        border: 1px solid {c["LINE_DARK"]};
        border-radius: {r["md"]}px;
        background: #ffffff;
    }}
    QFrame#history-head {{
        min-height: 34px;
        background: #f7f9fc;
        border-bottom: 1px solid {c["LINE"]};
        color: #405066;
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_BLACK};
    }}
    QFrame#history-item {{
        min-height: 30px;
        border-radius: {r["xs"]}px;
        background: transparent;
    }}
    QFrame#history-item:hover {{
        background: {c["SELECT_BG"]};
    }}
    QPushButton#history-pick {{
        border: none;
        background: transparent;
        color: {c["TEXT"]};
        font-family: Consolas, "Courier New", monospace;
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_BOLD};
        text-align: left;
        min-height: 28px;
    }}
    QPushButton#history-delete {{
        border: none;
        background: transparent;
        color: {c["MUTED"]};
        font-size: {theme.FS_MD}pt;
        font-weight: {theme.FW_BOLD};
        min-height: 28px;
    }}
    QPushButton#history-delete:hover {{
        color: {c["DANGER"]};
    }}
    QCheckBox#check-label {{
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_BOLD};
        color: {c["TEXT"]};
        spacing: 4px;
    }}
    """
