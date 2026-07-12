"""
设计令牌（Design Tokens）

迁移自原型 assets/hmi/css/tokens.css，是 PySide6 主题的唯一真相源。
修改本文件必须同步更新 docs/hmi/ui-restoration-spec.md §1 令牌表。

来源对照：
  颜色 → tokens.css 的 :root 变量 + 散落写死色（spec §1.2）
  字号 → spec §2.2（5 档：11/12/13/14/24px）
  字重 → spec §2.3（3 档：700/800/900，无 normal）
  圆角 → spec §3.1（5 档：4/5/6/8/999px）
  控件高 → spec §3.2（基准 32px）
  阴影 → tokens.css --shadow（全站唯一）
"""
from PySide6.QtGui import QColor

# === 基础语义色（对应 :root 16 个变量） ===
BG = QColor("#d8dee7")              # 页面背景（窗体外灰蓝底）
WINDOW = QColor("#f7f9fc")          # 桌面窗体背景
CHROME = QColor("#edf2f7")          # 工具栏背景
PANEL = QColor("#ffffff")           # 面板白
LINE = QColor("#cfd8e3")            # 主分隔线 / 卡片边框（浅）
LINE_DARK = QColor("#aeb9c8")       # 输入框 / 按钮边框（深）
TEXT = QColor("#17202c")            # 主文本
MUTED = QColor("#617083")           # 次要文本 / 标签
PRIMARY = QColor("#0b6fb3")         # 主色（按钮 / 选中态）
PRIMARY_DARK = QColor("#07588e")    # 主色按下 / 按钮边框
OK = QColor("#11875d")              # 在线 / 正常（绿）
WARN = QColor("#b86b00")            # 告警 / 未确认（橙）
DANGER = QColor("#bf3a46")          # 危险 / 删除（红）
CONSOLE_BG = QColor("#101a27")      # 终端深色背景
CONSOLE_TEXT = QColor("#dceafe")    # 终端浅蓝文字

# === 散落写死色（spec §1.2，原型未走变量） ===
TITLEBAR_BG = QColor("#182231")
TITLEBAR_FG = QColor("#ffffff")
TITLEBAR_SUB = QColor("#d6e2ef")
WINBTN_MIN = QColor("#5aa0d8")
WINBTN_MAX = QColor("#d8aa37")
WINBTN_CLOSE = QColor("#d95d5d")
WINBTN_IDLE = QColor("#8796a8")
MENUBAR_BG = QColor("#f4f7fb")
MENUBAR_FG = QColor("#293648")
WORKSPACE_BG = QColor("#e5ebf2")
SIDEBAR_BG = QColor("#f8fafc")
PANE_TITLE_BG = QColor("#f1f5f9")
TH_BG = QColor("#f1f5f9")
TH_FG = QColor("#405066")
SELECT_BG = QColor("#e9f4ff")       # 选中态背景（树/标签/表格行）
SELECT_BORDER_TREE = QColor("#9bc6e8")
SELECT_BORDER_TAB = QColor("#b9cce0")
SELECT_BORDER_ROW = QColor("#b7d8f2")
TAG_BG = QColor("#e8edf4")
TAG_FG = QColor("#46566a")
TAG_OK_BG = QColor("#e8f6ef")
TAG_WARN_BG = QColor("#fff4df")
RX_COLOR = QColor("#7dd3fc")        # 终端 RX 行方向色
TX_COLOR = QColor("#86efac")        # 终端 TX 行方向色
DISABLED_BORDER = QColor("#c5ced8")
DISABLED_BG = QColor("#e5eaf0")
DISABLED_FG = QColor("#7b8795")
DANGER_BORDER = QColor("#9f2632")
WINDOW_BORDER = QColor("#9eabba")
ROW_HOVER_BG = QColor("#f8fbff")
TOAST_BG = QColor("#17202c")
STATUSBAR_BG = QColor("#eef2f7")
STATUSBAR_FG = QColor("#405066")

# === 字号（5 档，单位 pt） ===
# 注意：原型用 px，PySide6 用 pt。pt 在高 DPI 下更稳定。
# 9pt ≈ 12px，对应换算：11px→8pt, 12px→9pt, 13px→10pt, 14px→11pt, 24px→18pt
FS_XS = 8    # 11px：标签 .tag
FS_SM = 9    # 12px：tool-label / 终端 / 状态栏 / metric-label
FS_MD = 10   # 13px：菜单栏 / select / input / btn / 表格（最常用）
FS_LG = 11   # 14px：action-body / toast
FS_XL = 18   # 24px：metric-value（大数值）

# === 字重（3 档，无 normal） ===
FW_REGULAR = 700   # 菜单栏 / 表格 td（最轻档）
FW_BOLD = 800      # 按钮 / 输入框 / 标签（最常用）
FW_BLACK = 900     # 标题 / 数值 / metric-value

# === 圆角（5 档，单位 px） ===
RADIUS_XS = 4     # 菜单项 / 历史项
RADIUS_SM = 5     # 输入控件 / 按钮（最常用）
RADIUS_MD = 6     # 卡片 / 标签页 / 图表
RADIUS_LG = 8     # 窗体 / 模态 / toast
RADIUS_PILL = 999 # 标签胶囊

# === 控件基准高度 ===
CONTROL_H = 32    # btn / select / input / tree-item / tab 基准高

# === 窗口网格行高（5 行 grid） ===
ROW_TITLEBAR = 34
ROW_MENUBAR = 34
ROW_TOOLBAR_MIN = 50  # 最小高度（工具栏两行会更高）
ROW_STATUSBAR = 28

# === 色值字符串（QSS 用，QColor.name() 返回 #rrggbb） ===
def _hex(c: QColor) -> str:
    return c.name()

# 供 QSS 字符串拼接用的色值表（避免每次 .name()）
HEX = {k: v.name() for k, v in dict(globals()).items() if isinstance(v, QColor)}
