"""
页面注册表

定义所有页面的元数据（id/名称/图标/分组/标签），是侧边栏、tabs、路由的共同数据源。
对应原型 mock.js 的 pages 数组 + index.html 的 tree 结构。

新增页面只需在此表加一项，侧边栏/tabs/路由自动跟随。
"""
from dataclasses import dataclass


@dataclass
class PageMeta:
    """页面元数据"""
    page_id: str          # 路由键（唯一）
    name: str             # 显示名（侧边栏/tabs/标题）
    icon: str             # 图标 key（对应 icons.py 的 _ICONS 字典键）
    group: str            # 分组（"设备"/"数据"/"AI"）
    tag: str = ""         # 右侧标签文案（如"3"/"COM3"/"4 点"）
    tag_type: str = ""    # 标签类型（""默认/"ok"/"warn"，控制颜色）

    def __post_init__(self):
        if not self.tag_type and self.tag:
            self.tag_type = "default"


# 10 个页面的注册顺序 = tabs 顺序
PAGES: list[PageMeta] = [
    # === 设备 ===
    PageMeta("overview",    "设备总览", "dashboard",  "设备", "3", "ok"),
    PageMeta("serial",      "串口连接", "connection", "设备", "COM3", "ok"),
    PageMeta("monitor",     "实时监控", "activity",   "设备", "2 点"),
    PageMeta("statusPolicy","状态策略", "shield",     "设备", "10 min"),
    PageMeta("params",      "参数配置", "sliders",    "设备", "已同步"),
    # === 数据 ===
    PageMeta("alarms",      "报警记录", "bell",       "数据", "1", "warn"),
    PageMeta("history",     "历史数据", "clock",      "数据", "CSV"),
    PageMeta("settings",    "系统设置", "wrench",     "数据", "v0.1"),
    # === AI ===
    PageMeta("aiAssistant", "AI 助手",  "sparkles",   "AI", "对话"),
    PageMeta("modelConfig", "模型配置", "cpu",        "AI", "设置"),
]

# 分组顺序（侧边栏按此顺序渲染）
GROUPS: list[str] = ["设备", "数据", "AI"]

# id → PageMeta 查找
PAGE_MAP: dict[str, PageMeta] = {p.page_id: p for p in PAGES}


def get_page(page_id: str) -> PageMeta | None:
    """按 id 查页面，未找到返回 None"""
    return PAGE_MAP.get(page_id)
