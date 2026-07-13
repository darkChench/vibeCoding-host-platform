"""
图标管理

用 QtSvg 渲染内嵌 SVG 路径生成 QIcon，不依赖外部文件。
SVG 路径风格：线性（stroke），参考 Feather Icons / Heroicons。
颜色由参数控制（默认 muted #617083，active 态主色蓝 #0b6fb3）。

用法：
    from src.icons import get_icon_pixmap
    pixmap = get_icon_pixmap("dashboard", size=18, color="#617083")
    label.setPixmap(pixmap)
"""
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import QByteArray, Qt
from . import theme


# 10 个图标的 SVG 路径（24x24 viewBox，stroke 风格）
# 参考 Feather Icons / Heroicons 的设计语言
_ICONS: dict[str, str] = {
    # overview 设备总览 — dashboard 仪表盘
    "dashboard": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
    </svg>''',

    # serial 串口连接 — plug/connection
    "connection": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 2v6"/>
        <path d="M15 2v6"/>
        <path d="M6 8h12v4a6 6 0 0 1-12 0V8z"/>
        <path d="M12 18v4"/>
        <path d="M8 22h8"/>
    </svg>''',

    # monitor 实时监控 — activity 脉冲线
    "activity": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>''',

    # statusPolicy 状态策略 — shield 盾牌
    "shield": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>''',

    # params 参数配置 — sliders 滑块
    "sliders": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="4" y1="21" x2="4" y2="14"/>
        <line x1="4" y1="10" x2="4" y2="3"/>
        <line x1="12" y1="21" x2="12" y2="12"/>
        <line x1="12" y1="8" x2="12" y2="3"/>
        <line x1="20" y1="21" x2="20" y2="16"/>
        <line x1="20" y1="12" x2="20" y2="3"/>
        <line x1="1" y1="14" x2="7" y2="14"/>
        <line x1="9" y1="8" x2="15" y2="8"/>
        <line x1="17" y1="16" x2="23" y2="16"/>
    </svg>''',

    # alarms 报警记录 — bell 铃铛
    "bell": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
    </svg>''',

    # history 历史数据 — clock 时钟
    "clock": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
    </svg>''',

    # settings 系统设置 — wrench 扳手
    "wrench": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
    </svg>''',

    # aiAssistant AI 助手 — sparkles 星光
    "sparkles": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 3l1.5 5L19 9.5 13.5 11 12 16l-1.5-5L5 9.5 10.5 8 12 3z"/>
        <path d="M19 16l.7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16z"/>
        <path d="M5 14l.5 1.7L7 16l-1.5.5L5 18l-.5-1.5L3 16l1.5-.3L5 14z"/>
    </svg>''',

    # modelConfig 模型配置 — cpu 芯片
    "cpu": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="4" y="4" width="16" height="16" rx="2"/>
        <rect x="9" y="9" width="6" height="6"/>
        <line x1="9" y1="1" x2="9" y2="4"/>
        <line x1="15" y1="1" x2="15" y2="4"/>
        <line x1="9" y1="20" x2="9" y2="23"/>
        <line x1="15" y1="20" x2="15" y2="23"/>
        <line x1="20" y1="9" x2="23" y2="9"/>
        <line x1="20" y1="14" x2="23" y2="14"/>
        <line x1="1" y1="9" x2="4" y2="9"/>
        <line x1="1" y1="14" x2="4" y2="14"/>
    </svg>''',
}


def get_icon_pixmap(icon_key: str, size: int = 18, color: str | None = None) -> QPixmap:
    """渲染 SVG 图标为 QPixmap。

    用 render(painter, QRectF) 指定内缩渲染区域，给 stroke 描边留余量不被裁。
    QRectF 用逻辑坐标（painter 已设 devicePixelRatio）。

    Args:
        icon_key: 图标键（如 'dashboard'）
        size: 最终显示像素尺寸（默认 18）
        color: 颜色（默认用 theme.MUTED）
    Returns:
        QPixmap，失败返回空 pixmap
    """
    svg_template = _ICONS.get(icon_key)
    if not svg_template:
        return QPixmap()

    if color is None:
        color = theme.HEX["MUTED"]

    svg_str = svg_template.replace("{color}", color)
    svg_bytes = QByteArray(svg_str.encode("utf-8"))

    renderer = QSvgRenderer(svg_bytes)
    if not renderer.isValid():
        return QPixmap()

    from PySide6.QtGui import QGuiApplication
    from PySide6.QtCore import QRectF
    dpr = QGuiApplication.primaryScreen().devicePixelRatio()

    # pixmap 物理尺寸 = size * dpr，逻辑尺寸 = size
    pixmap = QPixmap(int(size * dpr), int(size * dpr))
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.GlobalColor.transparent)

    # 渲染区域内缩 3 逻辑像素（每边），给 stroke-width=2 的溢出留余量
    pad = 3.0
    rect = QRectF(pad, pad, size - pad * 2, size - pad * 2)

    painter = QPainter(pixmap)
    renderer.render(painter, rect)
    painter.end()

    return pixmap


def get_active_icon_pixmap(icon_key: str, size: int = 18) -> QPixmap:
    """active 态图标（主色蓝）"""
    return get_icon_pixmap(icon_key, size, theme.HEX["PRIMARY"])


_ARROW_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 8" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="1 1.5 6 6 11 1.5"/>
</svg>'''


def get_arrow_pixmap(color: str | None = None, width: int = 12, height: int = 8) -> QPixmap:
    """生成下拉箭头 QPixmap（V 形）"""
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtGui import QPixmap, QPainter, QGuiApplication
    from PySide6.QtCore import QByteArray, Qt

    if color is None:
        color = theme.HEX["MUTED"]

    svg_str = _ARROW_SVG.replace("{color}", color)
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    if not renderer.isValid():
        return QPixmap()

    dpr = QGuiApplication.primaryScreen().devicePixelRatio()
    pm = QPixmap(int(width * dpr), int(height * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return pm
