"""
全局 QSS 样式生成

迁移自原型 assets/hmi/css/widgets.css 的核心控件样式。
QSS 不支持 CSS 变量，色值从 theme.py 的 HEX 字典读取后拼接成 QSS 字符串。

用法：在 app.py 里读 theme.py 颜色 → 调 build_qss() → app.setStyleSheet()
"""
from . import theme


def build_qss() -> str:
    """生成全局 QSS 字符串"""
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
    QLineEdit, QComboBox {{
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

    /* ===== 表格 ===== */
    QTableWidget {{
        border: 1px solid {c["LINE"]};
        border-radius: {r["md"]}px;
        background: #ffffff;
        gridline-color: {c["LINE"]};
        font-size: {theme.FS_MD}pt;
    }}
    QTableWidget::item {{
        padding: 6px 8px;
        border-bottom: 1px solid {c["LINE"]};
    }}
    QTableWidget::item:hover {{
        background: {c["ROW_HOVER_BG"]};
    }}
    QTableWidget::item:selected {{
        background: {c["SELECT_BG"]};
    }}
    QHeaderView::section {{
        background: {c["TH_BG"]};
        color: {c["TH_FG"]};
        font-weight: {theme.FW_BOLD};
        padding: 6px 8px;
        border: none;
        border-bottom: 1px solid {c["LINE"]};
    }}

    /* ===== 标签 tag ===== */
    QLabel#tag {{
        border-radius: 10px;
        padding: 3px 8px;
        min-height: 16px;
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
    """
