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
    QFrame#workspace {{
        background: {c["WORKSPACE_BG"]};
    }}
    """
