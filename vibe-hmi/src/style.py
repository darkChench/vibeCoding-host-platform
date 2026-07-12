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

    /* ===== 标题栏 ===== */
    QFrame#titlebar {{
        background: {c["TITLEBAR_BG"]};
        min-height: {theme.ROW_TITLEBAR}px;
        max-height: {theme.ROW_TITLEBAR}px;
    }}
    QLabel#titlebar-app {{
        color: {c["TITLEBAR_FG"]};
        font-weight: {theme.FW_BOLD};
        font-size: {theme.FS_MD}pt;
    }}
    QLabel#titlebar-center {{
        color: {c["TITLEBAR_SUB"]};
        font-size: {theme.FS_MD}pt;
    }}

    /* ===== 菜单栏 ===== */
    QFrame#menubar {{
        background: {c["MENUBAR_BG"]};
        min-height: {theme.ROW_MENUBAR}px;
        max-height: {theme.ROW_MENUBAR}px;
    }}
    QPushButton#menu-item {{
        min-height: 25px;
        padding: 0 10px;
        border: 1px solid transparent;
        border-radius: {r["xs"]}px;
        background: transparent;
        color: {c["MENUBAR_FG"]};
        font-size: {theme.FS_MD}pt;
        font-weight: {theme.FW_REGULAR};
    }}
    QPushButton#menu-item:hover {{
        border-color: {c["LINE"]};
        background: #ffffff;
    }}

    /* ===== 工具栏 ===== */
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

    /* ===== 状态栏 ===== */
    QFrame#statusbar {{
        background: {c["STATUSBAR_BG"]};
        min-height: {theme.ROW_STATUSBAR}px;
        max-height: {theme.ROW_STATUSBAR}px;
        border-top: 1px solid {c["LINE_DARK"]};
    }}
    QLabel#statusbar-text {{
        color: {c["STATUSBAR_FG"]};
        font-size: {theme.FS_SM}pt;
        font-weight: {theme.FW_REGULAR};
    }}

    /* ===== 工作区 ===== */
    QFrame#workspace {{
        background: {c["WORKSPACE_BG"]};
    }}

    /* ===== 桌面窗体外框 ===== */
    QFrame#desktop-window {{
        background: {c["WINDOW"]};
        border: 1px solid {c["WINDOW_BORDER"]};
        border-radius: {r["lg"]}px;
    }}
    """
