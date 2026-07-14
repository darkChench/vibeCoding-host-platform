# 组件样式参考手册

> 本文件记录 PySide6 上位机每个 UI 组件的**最终渲染样式值**（高度/宽度/边框/圆角/字号/颜色等），
> 是 `widget-qss-spec.md`（HTML→PySide6 映射规范）的运行时快照。
>
> 样式来源分三类：
> - **全局 QSS**（`src/style.py` 的 `build_qss()`）—— 大部分控件样式
> - **内联 QSS**（各 page 文件的 `setStyleSheet()`）—— 特定控件的局部覆盖
> - **代码属性**（`setFixedHeight` / `setFixedSize` 等）—— 尺寸约束
>
> 更新组件样式时，请同步更新本文件对应行。

---

## 1. 设计令牌（Design Tokens）

> 来源：`src/theme.py`，是所有色值/字号/圆角的唯一真相源。

### 1.1 颜色

| 令牌 | 色值 | 用途 |
|:---|:---|:---|
| `BG` | `#d8dee7` | 页面背景（窗体外灰蓝底） |
| `WINDOW` | `#f7f9fc` | 桌面窗体背景 |
| `CHROME` | `#edf2f7` | 工具栏背景 |
| `PANEL` | `#ffffff` | 面板白 |
| `LINE` | `#cfd8e3` | 主分隔线 / 卡片边框（浅） |
| `LINE_DARK` | `#aeb9c8` | 输入框 / 按钮边框（深） |
| `TEXT` | `#17202c` | 主文本 |
| `MUTED` | `#617083` | 次要文本 / 标签 |
| `PRIMARY` | `#0b6fb3` | 主色（按钮 / 选中态） |
| `PRIMARY_DARK` | `#07588e` | 主色按下 / 按钮边框 |
| `OK` | `#11875d` | 在线 / 正常（绿） |
| `WARN` | `#b86b00` | 告警 / 未确认（橙） |
| `DANGER` | `#bf3a46` | 危险 / 删除（红） |
| `CONSOLE_BG` | `#101a27` | 终端深色背景 |
| `WORKSPACE_BG` | `#e5ebf2` | 工作区背景 |
| `SIDEBAR_BG` | `#f8fafc` | 侧边栏背景 |
| `SELECT_BG` | `#e9f4ff` | 选中态背景 |
| `TAG_BG` | `#e8edf4` | 标签默认背景 |
| `TAG_FG` | `#46566a` | 标签默认文字 |
| `TAG_OK_BG` | `#e8f6ef` | 标签绿底 |
| `TAG_WARN_BG` | `#fff4df` | 标签橙底 |
| `TH_BG` | `#f1f5f9` | 表头背景 |
| `TH_FG` | `#405066` | 表头文字 |

### 1.2 字号（5 档，单位 pt）

| 令牌 | 值 | 对应 px | 用途 |
|:---|:---|:---|:---|
| `FS_XS` | 8pt | 11px | 标签 `.tag` |
| `FS_SM` | 9pt | 12px | tool-label / 状态栏 / metric-label / chip-text |
| `FS_MD` | 10pt | 13px | 菜单栏 / select / input / btn / 表格（最常用） |
| `FS_LG` | 11pt | 14px | card-title |
| `FS_XL` | 18pt | 24px | metric-value（大数值） |

### 1.3 字重（3 档，无 normal）

| 令牌 | 值 | 用途 |
|:---|:---|
| `FW_REGULAR` | 700 | 菜单栏 / 表格 |
| `FW_BOLD` | 800 | 按钮 / 输入框 / 标签（最常用） |
| `FW_BLACK` | 900 | 标题 / metric-value |

### 1.4 圆角（5 档，单位 px）

| 令牌 | 值 | 用途 |
|:---|:---|
| `RADIUS_XS` | 4px | 菜单项 / 圆点 |
| `RADIUS_SM` | 5px | 输入控件 / 按钮 |
| `RADIUS_MD` | 6px | 卡片 / 图表 |
| `RADIUS_LG` | 8px | 窗体 / 模态 |
| `RADIUS_PILL` | 999px | 标签胶囊（实际写 13px 更可靠） |

### 1.5 控件基准

| 令牌 | 值 | 用途 |
|:---|:---|
| `CONTROL_H` | 32px | btn / select / input / tree-item / tab 基准高 |

### 1.6 滚动条

| 属性 | 值 |
|:---|:---|
| 宽度/高度 | 10px |
| 手柄默认色 | `#a8b0bb` |
| 手柄 hover | `#8a93a0` |
| 手柄 pressed | `#6c7682` |
| 手柄圆角 | 4px |
| 手柄最小长度 | 30px |
| 轨道背景 | transparent |
| 两端箭头按钮 | 隐藏（`height/width: 0`） |

---

## 2. 窗口骨架

### 2.1 主窗口 MainWindow

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 默认尺寸 | 1220 × 760 | `main_window.py` |
| 最小尺寸 | 900 × 560 | `main_window.py` |
| 标题栏 | 系统原生 | — |

### 2.2 菜单栏 QMenuBar

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 背景 | `MENUBAR_BG` `#f4f7fb` | 全局 QSS |
| 文字色 | `MENUBAR_FG` `#293648` | 全局 QSS |
| 字号 | `FS_MD` 10pt | 全局 QSS |
| 字重 | `FW_REGULAR` 700 | 全局 QSS |
| 内边距 | 2px | 全局 QSS |
| 项内边距 | 4px 10px | 全局 QSS |
| 项选中背景 | `#ffffff` | 全局 QSS |
| 项选中边框 | 1px `LINE` | 全局 QSS |
| 项圆角 | `RADIUS_XS` 4px | 全局 QSS |

### 2.3 工具栏（自定义 QFrame#toolbar）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 背景 | `CHROME` `#edf2f7` | 全局 QSS |
| 底边框 | 1px `LINE` | 全局 QSS |
| 内边距 | 10px 8px | `main_window.py` |
| 行间距 | 6px | `main_window.py` |

### 2.4 工具栏下拉组（_make_tool_group）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 标签字号 | `FS_SM` 9pt | 全局 QSS `#tool-label` |
| 标签字重 | `FW_BOLD` 800 | 全局 QSS |
| 标签颜色 | `MUTED` | 全局 QSS |
| 下拉最小宽 | 80px（≤4项）/ 100px（>4项） | `main_window.py` |
| 组件间距 | 6px | `main_window.py` |

### 2.5 工具栏状态行

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 字号 | `FS_SM` 9pt | 全局 QSS `#stats-strip` |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| 正常态颜色 | `OK` `#11875d`（`#stat-ok`） | 全局 QSS |
| 告警态颜色 | `WARN` `#b86b00`（`#stat-warn`） | 全局 QSS |
| 项间距 | 12px | `main_window.py` |

### 2.6 状态栏 QStatusBar

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 背景 | `STATUSBAR_BG` `#eef2f7` | 全局 QSS |
| 文字色 | `STATUSBAR_FG` `#405066` | 全局 QSS |
| 字号 | `FS_SM` 9pt | 全局 QSS |
| 顶边框 | 1px `LINE_DARK` | 全局 QSS |

---

## 3. 工作区布局

### 3.1 侧边栏 Sidebar

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 固定宽度 | 230px | `sidebar.py` |
| 背景 | `SIDEBAR_BG` `#f8fafc` | 全局 QSS `#sidebar` |
| 右边框 | 1px `LINE` | 全局 QSS |

### 3.2 侧边栏 pane-title

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 背景 | `PANE_TITLE_BG` `#f1f5f9` | 全局 QSS |
| 字号 | `FS_MD` 10pt | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| 固定高度 | 38px | 全局 QSS（min/max） |
| 内边距 | 0 12px | 全局 QSS |
| 底边框 | 1px `LINE` | 全局 QSS |

### 3.3 侧边栏树项 TreeItem（#tree-item）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 最小高度 | `CONTROL_H` 32px | 全局 QSS |
| 内边距 | 8px 0 8px 0 | `sidebar.py` |
| 三列间距 | 6px | `sidebar.py` |
| 默认背景 | transparent | 全局 QSS |
| 默认边框 | 1px transparent | 全局 QSS |
| 圆角 | `RADIUS_SM` 5px | 全局 QSS |
| hover 边框 | 1px `LINE` | 全局 QSS |
| hover 背景 | `#ffffff` | 全局 QSS |
| active 边框 | 1px `SELECT_BORDER_TREE` `#9bc6e8` | 全局 QSS |
| active 背景 | `SELECT_BG` `#e9f4ff` | 全局 QSS |

### 3.4 树项图标（#tree-icon）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 固定尺寸 | 24 × 24px | `sidebar.py` |
| 图标渲染尺寸 | 20px | `sidebar.py`（get_icon_pixmap） |
| 渲染内边距 | 3px（防描边裁剪） | `icons.py` |
| 默认色 | `MUTED` | 全局 QSS |
| active 色 | `PRIMARY` | 全局 QSS |

### 3.5 树项名称（#tree-name）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 字号 | `FS_MD` 10pt | 全局 QSS |
| 默认字重 | `FW_REGULAR` 700 | 全局 QSS |
| active 字重 | `FW_BOLD` 800 | 全局 QSS |
| active 色 | `PRIMARY` | 全局 QSS |

### 3.6 树项标签（#tree-tag）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 圆角 | `RADIUS_PILL` 999px | 全局 QSS |
| 内边距 | 3px 8px | 全局 QSS |
| 最小高度 | 16px | 全局 QSS |
| 字号 | `FS_XS` 8pt | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| 默认背景 | `TAG_BG` `#e8edf4` | 全局 QSS |
| 默认文字 | `TAG_FG` `#46566a` | 全局 QSS |
| ok 变体背景 | `TAG_OK_BG` `#e8f6ef` | 全局 QSS |
| ok 变体文字 | `OK` `#11875d` | 全局 QSS |
| warn 变体背景 | `TAG_WARN_BG` `#fff4df` | 全局 QSS |
| warn 变体文字 | `WARN` `#b86b00` | 全局 QSS |

### 3.7 主区 MainArea（#main-area）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 背景 | `#ffffff` | 全局 QSS |
| 右边框 | 1px `LINE` | 全局 QSS |

### 3.8 Tabs 行（#tabs-scroll）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 固定高度 | 40px | `main_area.py` |
| 背景 | `#f7f9fc` | 全局 QSS |
| 底边框 | 1px `LINE` | 全局 QSS |
| 内边距 | 8px 6px 8px 0 | `main_area.py` |
| Tab 间距 | 2px | `main_area.py` |

### 3.9 Tab 按钮（#tab）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 最小高度 | `CONTROL_H` 32px | 全局 QSS |
| 内边距 | 0 12px | 全局 QSS |
| 边框 | 1px `LINE`（底边 none） | 全局 QSS |
| 左上圆角 | `RADIUS_MD` 6px | 全局 QSS |
| 右上圆角 | `RADIUS_MD` 6px | 全局 QSS |
| 默认背景 | `CHROME` `#edf2f7` | 全局 QSS |
| 默认文字色 | `#35465a` | 全局 QSS |
| 字号 | `FS_MD` 10pt | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| checked 背景 | `#ffffff` | 全局 QSS |
| checked 文字色 | `PRIMARY` | 全局 QSS |
| checked 边框 | `SELECT_BORDER_TAB` `#b9cce0` | 全局 QSS |

---

## 4. 通用控件

### 4.1 按钮 QPushButton

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 最小高度 | `CONTROL_H` 32px | 全局 QSS |
| 内边距 | 0 11px | 全局 QSS |
| 边框 | 1px `PRIMARY_DARK` | 全局 QSS |
| 圆角 | `RADIUS_SM` 5px | 全局 QSS |
| 默认背景 | `PRIMARY` `#0b6fb3` | 全局 QSS |
| 默认文字色 | `#ffffff` | 全局 QSS |
| 字号 | `FS_MD` 10pt | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| hover 背景 | `PRIMARY_DARK` | 全局 QSS |

#### secondary 变体 `[variant="secondary"]`

| 属性 | 值 |
|:---|:---|
| 边框色 | `LINE_DARK` `#aeb9c8` |
| 背景 | `#ffffff` |
| 文字色 | `TEXT` |
| hover 背景 | `#eef3f8` |

#### danger 变体 `[variant="danger"]`

| 属性 | 值 |
|:---|:---|
| 背景 | `DANGER` `#bf3a46` |
| 边框色 | `DANGER_BORDER` `#9f2632` |

#### disabled 状态

| 属性 | 值 |
|:---|:---|
| 边框色 | `DISABLED_BORDER` `#c5ced8` |
| 背景 | `DISABLED_BG` `#e5eaf0` |
| 文字色 | `DISABLED_FG` `#7b8795` |

### 4.2 输入框 QLineEdit

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 最小高度 | `CONTROL_H` 32px | 全局 QSS |
| 内边距 | 0 9px | 全局 QSS |
| 边框 | 1px `LINE_DARK` | 全局 QSS |
| 圆角 | `RADIUS_SM` 5px | 全局 QSS |
| 背景 | `#ffffff` | 全局 QSS |
| 字号 | `FS_MD` 10pt | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| focus 边框色 | `PRIMARY` | 全局 QSS |

### 4.3 下拉框 QComboBox

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 最小高度 | `CONTROL_H` 32px | 全局 QSS |
| 内边距 | 0 9px | 全局 QSS |
| 边框 | 1px `LINE_DARK` | 全局 QSS |
| 圆角 | `RADIUS_SM` 5px | 全局 QSS |
| 背景 | `#ffffff` | 全局 QSS |
| 字号 | `FS_MD` 10pt | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| focus/hover 边框色 | `PRIMARY` | 全局 QSS |
| 下拉箭头宽度 | 24px | 全局 QSS |
| 箭头图标 | `assets/icons/arrow-down.svg`（12×8px） | 全局 QSS |
| 弹窗边框 | 1px `LINE_DARK` | 全局 QSS |
| 弹窗项最小高度 | 28px | 全局 QSS |
| 弹窗项内边距 | 0 10px | 全局 QSS |
| 弹窗项 hover 背景 | `SELECT_BG` | 全局 QSS |
| 弹窗项 hover 文字色 | `PRIMARY` | 全局 QSS |

### 4.4 复选框 QCheckBox

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 表格内复选框 | 居中放在 container QWidget 中 | `params_page.py` |
| container 内边距 | 0 | `params_page.py` |
| container 对齐 | AlignCenter | `params_page.py` |

### 4.5 表格 QTableWidget

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 边框 | 1px `LINE` | 全局 QSS |
| 圆角 | `RADIUS_MD` 6px | 全局 QSS |
| 背景 | `#ffffff` | 全局 QSS |
| 网格线色 | transparent（隐藏竖线） | 全局 QSS |
| 字号 | `FS_MD` 10pt | 全局 QSS |
| 焦点策略 | NoFocus（禁用虚线框） | `params_page.py` |
| 行号 | 隐藏 | `params_page.py` |
| 表头背景 | `TH_BG` `#f1f5f9` | 全局 QSS |
| 表头文字色 | `TH_FG` `#405066` | 全局 QSS |
| 表头字重 | `FW_BOLD` 800 | 全局 QSS |
| 表头内边距 | 6px 4px | 全局 QSS |
| 行底边框 | 1px `LINE` | 全局 QSS |
| hover 背景 | `ROW_HOVER_BG` `#f8fbff` | 全局 QSS |
| 选中背景 | `SELECT_BG` | 全局 QSS |
| 选中文字色 | `PRIMARY_DARK` | 全局 QSS |
| 参数表固定高度 | 210px（5 行可见） | `params_page.py` |

---

## 5. 卡片（Card）

### 5.1 卡片容器 QFrame#card

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 边框 | 1px `LINE` | 全局 QSS |
| 圆角 | `RADIUS_MD` 6px | 全局 QSS |
| 背景 | `#ffffff` | 全局 QSS |

### 5.2 卡片头 QFrame#card-head

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 最小高度 | 36px | 全局 QSS |
| 背景 | `#f7f9fc` | 全局 QSS |
| 底边框 | 1px `LINE` | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| 内边距 | 10px 0 10px 0 | 各 page 文件 |

### 5.3 卡片标题 QLabel#card-title

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 字号 | `FS_LG` 11pt | 全局 QSS |
| 字重 | `FW_BLACK` 900 | 全局 QSS |

### 5.4 卡片标签 QLabel#tag

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 圆角 | 10px | 全局 QSS |
| 内边距 | 2px 8px | 全局 QSS |
| 最小高度 | 14px | 全局 QSS |
| 固定高度（实例） | 18px | 各 page 文件 |
| 字号 | `FS_XS` 8pt | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| 默认背景 | `TAG_BG` `#e8edf4` | 全局 QSS |
| warn 变体 | `TAG_WARN_BG` + `WARN` | 全局 QSS |
| ok 变体 | `TAG_OK_BG` + `OK` | 全局 QSS |

---

## 6. 参数配置页专属

### 6.1 设备地址输入框（slave_input）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 固定宽度 | 60px | `params_page.py` |
| 对齐 | 居中 | `params_page.py` |
| 占位符 | "1-247" | `params_page.py` |
| 校验范围 | 1-247 | `params_page.py` |

### 6.2 表单字段 label

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 颜色 | `MUTED` | `params_page.py`（内联） |
| 字号 | `FS_SM` 9pt | `params_page.py`（内联） |
| 字重 | `FW_BOLD` 800 | `params_page.py`（内联） |
| label-input 间距 | 4px | `params_page.py` |

### 6.3 表单网格（QGridLayout）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 内边距 | 14px | `params_page.py` |
| 水平间距 | 12px | `params_page.py` |
| 垂直间距 | 14px | `params_page.py` |
| 列数 | 2（等宽 stretch） | `params_page.py` |

### 6.4 表单按钮行

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 按钮间距 | 8px | `params_page.py` |

---

## 7. 实时监控页专属

### 7.1 Metric 卡 QFrame#metric

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 边框 | 1px `LINE` | 全局 QSS |
| 圆角 | `RADIUS_MD` 6px | 全局 QSS |
| 背景 | `#f8fafc` | 全局 QSS |
| 内边距 | 10px | `monitor_page.py` |
| 最小高度 | 78px | 全局 QSS |
| 网格列数 | 2（每行 2 张卡） | `monitor_page.py` |
| 网格间距 | 10px（水平/垂直） | `monitor_page.py` |

### 7.2 Metric 标签 QLabel#metric-label

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 颜色 | `MUTED` | 全局 QSS |
| 字号 | `FS_SM` 9pt | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |

### 7.3 Metric 数值 QLabel#metric-value

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 字号 | `FS_XL` 18pt | 全局 QSS |
| 字重 | `FW_BLACK` 900 | 全局 QSS |
| 单位 | `<small>` 标签 + `MUTED` 色 | `monitor_page.py`（内联富文本） |
| 对齐 | 左下 | `monitor_page.py` |

### 7.4 曲线筛选 chip QFrame#curve-chip

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 固定高度 | 26px | `monitor_page.py` |
| 内边距 | 10px 0 10px 0 | `monitor_page.py` |
| 圆点-文字间距 | 6px | `monitor_page.py` |
| 边框 | 1px `LINE` | 全局 QSS |
| 圆角 | 13px（= 高度一半，胶囊形） | 全局 QSS |
| 默认背景 | `#f8fafc` | 全局 QSS |
| hover 边框色 | `PRIMARY` | 全局 QSS |
| hover 背景 | `SELECT_BG` `#e9f4ff` | 全局 QSS |
| 隐藏态边框 | dashed `LINE` | 全局 QSS `[hidden="true"]` |
| 隐藏态背景 | `#f1f5f9` | 全局 QSS |
| WA_StyledBackground | True（确保 QSS 圆角生效） | `monitor_page.py` |

#### chip 圆点（QLabel）

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 固定尺寸 | 8 × 8px | `monitor_page.py` |
| 圆角 | 4px（正圆） | `monitor_page.py`（内联） |
| 可见态背景色 | 曲线调色板色（按索引） | `monitor_page.py`（内联） |
| 隐藏态背景色 | `#aab6c4` | `monitor_page.py`（内联） |

#### chip 文字 QLabel#chip-text

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 字号 | `FS_SM` 9pt | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| 可见态文字色 | `TEXT` | `monitor_page.py`（内联） |
| 隐藏态文字色 | `MUTED` | `monitor_page.py`（内联） |
| 隐藏态删除线 | font.setStrikeOut(True) | `monitor_page.py` |
| 背景 | transparent | `monitor_page.py`（内联） |

#### 曲线调色板 PALETTE

| 索引 | 色值 | 语义 |
|:---|:---|:---|
| 0 | `#0b6fb3` | 主色蓝（temperature） |
| 1 | `#11875d` | 绿（pressure） |
| 2 | `#b86b00` | 橙（P20） |
| 3 | `#bf3a46` | 红（PPM20） |
| 4 | `#617083` | 灰 |
| 5 | `#07588e` | 深蓝 |

> 颜色按采样参数在列表中的索引固定分配，不随显隐变化。

### 7.5 时间范围下拉框 range_combo

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 最小高度 | 26px | `monitor_page.py`（内联 QSS） |
| 内边距 | 0 6px | `monitor_page.py`（内联 QSS） |
| 字号 | `FS_MD` 10pt | `monitor_page.py`（内联 QSS） |
| 下拉箭头宽 | 16px | `monitor_page.py`（内联 QSS） |
| 档位 | 1分钟 / 10分钟 / 1小时 / 1天 | `monitor_page.py` |

### 7.6 暂停/继续按钮 btn_pause

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 固定高度 | 26px | `monitor_page.py` |
| 最小高度（QSS覆盖） | 26px | `monitor_page.py`（内联 QSS） |
| 内边距 | 0 10px | `monitor_page.py`（内联 QSS） |
| 变体 | secondary | `monitor_page.py` |
| 垂直对齐 | AlignVCenter | `monitor_page.py` |

### 7.7 QtCharts 图表

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 绘图区背景 | `#fbfdff`（浅蓝） | `monitor_page.py` |
| 绘图区边框 | 无（NoPen） | `monitor_page.py` |
| QChartView 背景 | `#ffffff` | `monitor_page.py` |
| 图例外边距 | 0 | `monitor_page.py` |
| QChart margins | 0 0 0 0 | `monitor_page.py` |
| 网格线色 | `#eef3f8`（极淡） | `monitor_page.py` |
| 曲线线宽 | 1.6px | `monitor_page.py` |
| 反锯齿 | Antialiasing | `monitor_page.py` |
| 图例 | 隐藏 | `monitor_page.py` |
| 趋势窗口上限 | 360 点 | `monitor_page.py` |

#### X 轴（QDateTimeAxis）

| 属性 | 值 |
|:---|:---|
| 格式 | `HH:mm:ss`（1分/10分/1小时）/ `HH:mm`（1天） |
| 刻度数 | 6 |
| 标题 | "时间" |
| 标题色 | `MUTED` |
| 标签色 | `MUTED` |

#### Y 轴（QValueAxis）

| 属性 | 值 |
|:---|:---|
| 刻度数 | 5 |
| 范围 | 自动（可见曲线 min/max + 10% 余量） |
| 标题 | 仅 1 条可见曲线时显示"显示名 (单位)" |
| 标签色 | `MUTED` |

### 7.8 空态 QLabel#empty-state

| 属性 | 值 | 来源 |
|:---|:---|:---|
| 颜色 | `MUTED` | 全局 QSS |
| 字号 | `FS_MD` 10pt | 全局 QSS |
| 字重 | `FW_BOLD` 800 | 全局 QSS |
| 对齐 | 居中 | `monitor_page.py` |
| 最小高度 | 120px | `monitor_page.py` |

---

## 8. 时间范围与采样间隔

| 档位 | 总跨度 | 采样间隔 | X 轴格式 | 窗口点数（约） |
|:---|:---|:---|:---|:---|
| 1 分钟 | 60s | 1s | HH:mm:ss | ~60 |
| 10 分钟 | 600s | 2s | HH:mm:ss | ~300 |
| 1 小时 | 3600s | 10s | HH:mm:ss | ~360 |
| 1 天 | 86400s | 240s | HH:mm | ~360 |

> 窗口点数上限固定 360，无论选多长时间范围，内存和渲染稳定。

---

## 9. 样式维护规则

1. **改全局 QSS**：修改 `src/style.py` → 同步更新本文件对应行
2. **改内联 QSS**：修改各 page 文件的 `setStyleSheet()` → 同步更新本文件对应行
3. **改尺寸**：修改 `setFixedHeight/Width` → 同步更新本文件对应行
4. **改设计令牌**：修改 `src/theme.py` → 更新 §1 → 检查本文件所有引用该令牌的行
5. **新增组件**：在本文件新增一节，记录所有样式属性和来源
