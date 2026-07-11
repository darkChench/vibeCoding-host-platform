<!-- markdownlint-disable MD013 MD033 -->
# 界面还原规范 · 总则与设计令牌

> 用途：把 `assets/hmi/page-interaction-review-prototype.html`（下称"原型"）的设计系统固化为 PySide6 可直接消费的令牌与规则，让 Qt 重写达到像素级还原、零歧义。
>
> 本文件是规范体系的**总入口**。先读本文件掌握令牌与全局结构，再按需查阅另外三份：
>
> - [控件映射规范（HTML → PySide6 → QSS）](widget-qss-spec.md)
> - [页面布局规范（8 页面逐一）](page-layout-spec.md)
> - [交互规范（导航/状态机/异常态）](interaction-spec.md)

---

## 1. 设计令牌 · 颜色

颜色是高还原度的核心。下表把原型 `:root` 里的 16 个 CSS 变量与散落在选择器里写死的颜色**统一命名**，作为 PySide6 主题常量（建议放进一个 `theme.py` 或 QSS `:root` 等价常量集）。

### 1.1 基础语义色（原型 `:root` 已声明）

| 令牌名 | 原型变量 | 色值 | 用途 |
| :--- | :--- | :--- | :--- |
| `color_bg` | `--bg` | `#d8dee7` | body 页面背景（窗体外灰蓝底） |
| `color_window` | `--window` | `#f7f9fc` | 桌面窗体背景 |
| `color_chrome` | `--chrome` | `#edf2f7` | 工具栏背景 |
| `color_panel` | `--panel` | `#ffffff` | 面板白（原型多用 `#fff` 字面量） |
| `color_line` | `--line` | `#cfd8e3` | 主分隔线 / 卡片边框 / 表格下边框（浅） |
| `color_line_dark` | `--line-dark` | `#aeb9c8` | 输入框 / 按钮边框 / 状态栏顶边（深） |
| `color_text` | `--text` | `#17202c` | 主文本 |
| `color_muted` | `--muted` | `#617083` | 次要文本 / 标签 |
| `color_primary` | `--primary` | `#0b6fb3` | 主色（按钮 / 选中态字 / 图标） |
| `color_primary_dark` | `--primary-dark` | `#07588e` | 主色按下 / 按钮边框 / hover |
| `color_ok` | `--ok` | `#11875d` | 在线 / 正常（绿） |
| `color_warn` | `--warn` | `#b86b00` | 告警 / 未确认 / 未保存（橙） |
| `color_danger` | `--danger` | `#bf3a46` | 危险 / 删除（红） |
| `color_console_bg` | `--console` | `#101a27` | 终端深色背景 |
| `color_console_text` | `--console-text` | `#dceafe` | 终端浅蓝文字 |
| `shadow_window` | `--shadow` | `0 18px 45px rgba(22,34,51,.18)` | 全站唯一阴影值 |

### 1.2 散落写死色（原型未走变量，需补成常量）

| 令牌名 | 色值 | 出处 / 用途 |
| :--- | :--- | :--- |
| `color_titlebar_bg` | `#182231` | 标题栏深色背景 |
| `color_titlebar_fg` | `#ffffff` | 标题栏主文字 |
| `color_titlebar_sub` | `#d6e2ef` | 标题栏副文字（居中标题） |
| `color_winbtn_min` | `#5aa0d8` | 窗口按钮 · 最小化（蓝） |
| `color_winbtn_max` | `#d8aa37` | 窗口按钮 · 最大化（黄） |
| `color_winbtn_close` | `#d95d5d` | 窗口按钮 · 关闭（红） |
| `color_winbtn_idle` | `#8796a8` | 窗口按钮未激活态（灰） |
| `color_menubar_bg` | `#f4f7fb` | 菜单栏背景 |
| `color_menubar_fg` | `#293648` | 菜单栏文字 |
| `color_workspace_bg` | `#e5ebf2` | 工作区灰底（侧边栏与主区之间） |
| `color_sidebar_bg` | `#f8fafc` | 侧边栏背景 |
| `color_pane_title_bg` | `#f1f5f9` | 面板标题 / 表头背景 |
| `color_th_fg` | `#405066` | 表格表头字色 |
| `color_select_bg` | `#e9f4ff` | 选中态背景（树 / 标签 / 表格行） |
| `color_select_fg` | `= color_primary` | 选中态字色 |
| `color_select_border_tree` | `#9bc6e8` | 树选中边框 |
| `color_select_border_tab` | `#b9cce0` | 标签页选中边框 |
| `color_select_border_row` | `#b7d8f2` | 表格行选中内描边 |
| `color_tag_bg` | `#e8edf4` | 中性标签背景 |
| `color_tag_fg` | `#46566a` | 中性标签字色 |
| `color_tag_ok_bg` | `#e8f6ef` | OK 标签背景 |
| `color_tag_warn_bg` | `#fff4df` | 告警标签背景 |
| `color_rx` | `#7dd3fc` | 终端 RX 行方向色（浅蓝） |
| `color_tx` | `#86efac` | 终端 TX 行方向色（浅绿） |
| `color_disabled_border` | `#c5ced8` | 禁用控件边框 |
| `color_disabled_bg` | `#e5eaf0` | 禁用控件背景 |
| `color_disabled_fg` | `#7b8795` | 禁用控件字色 |
| `color_danger_border` | `#9f2632` | 危险按钮边框 |
| `color_edit_focus_bg` | `#fff8e6` | 可编辑单元格聚焦背景 |
| `color_edit_focus_border` | `#e6a700` | 可编辑单元格聚焦内描边 |
| `color_row_hover_bg` | `#f8fbff` | 表格行 hover 背景 |
| `color_toast_bg` | `#17202c` | Toast 背景 |
| `color_modal_scrim` | `rgba(15,23,42,.42)` | 模态遮罩 |
| `color_history_del_hover_bg` | `#fff1f2` | 历史删除 hover 背景 |
| `color_history_del_hover_border` | `#efb2b8` | 历史删除 hover 边框 |
| `color_window_border` | `#9eabba` | 窗体 / 模态外框 |

---

## 2. 设计令牌 · 字体

### 2.1 字族

| 令牌名 | 字族栈 | 用途 |
| :--- | :--- | :--- |
| `font_sans` | `"Microsoft YaHei", "PingFang SC", Arial, sans-serif` | 正文 / 控件 / 表格 |
| `font_mono` | `Consolas, "Courier New", monospace` | 终端 / 发送框 / 历史项 / Markdown 输出 |

> PySide6 还原：`setFont(QFont("Microsoft YaHei", ...))`；等宽区单独设 `QFont("Consolas")`。macOS 上 "PingFang SC" 优先，Windows 上 "Microsoft YaHei" 优先——字族栈已兼容。

### 2.2 字号档位（全站仅 5 档）

| 令牌 | 值 | 用处 |
| :--- | :--- | :--- |
| `fs_xs` | `11px` | 标签 `.tag` |
| `fs_sm` | `12px` | tool-label / stats-strip / tree-heading / console-tab / 终端 / check-label / 状态栏 / metric-label / field label / history-head / markdown 输出 |
| `fs_md` | `13px` | 标题栏副文字 / 菜单栏 / 菜单项 / select / input / btn / tree-item / tab / 表格 / review-table / metric-value 单位 |
| `fs_lg` | `14px` | action-body / toast |
| `fs_xl` | `24px` | metric-value（大数值） |

### 2.3 字重档位（全站仅 3 档，无 `normal/400`）

| 令牌 | 值 | 用处 |
| :--- | :--- | :--- |
| `fw_regular` | `700` | 菜单栏 / 菜单项 / tree-item / 状态栏 / 表格 td 主体 |
| `fw_bold` | `800` | app-mark / tool-label / select / input / btn / stats-strip / pane-title / tree-heading / tree-icon / tag / tab / console-tab / send-input / history-item / card-head / metric-label / field label / rx / tx |
| `fw_black` | `900` | history-head / history-delete / modal-head / metric-value / quick-icon / quick-title / review-table th / review-table 首列 |

> **关键还原规律**：本设计**没有 `normal/400` 正文**，所有可读文字至少 `700`。PySide6 中 `QFont::setBold(true)` 对应 `700`，更粗需 `QFont::setWeight(QFont::Black)` 或直接设字重数值。

---

## 3. 设计令牌 · 间距、圆角、控件高

### 3.1 圆角档位（全站仅 5 档）

| 令牌 | 值 | 用处 |
| :--- | :--- | :--- |
| `radius_xs` | `4px` | app-icon / menu-item / 菜单项按钮 / history-item / history-delete |
| `radius_sm` | `5px` | **所有输入控件与主按钮**：select / input / btn / tree-item / console-tab / send-input |
| `radius_md` | `6px` | 菜单弹窗 / tab（上圆角 `6px 6px 0 0`）/ 卡片 / metric / 图表 / quick-icon / quick-card / console / history-popover / action-box / review-table-wrap / markdown 输出 |
| `radius_lg` | `8px` | 窗体 / 模态 / action-modal / toast |
| `radius_pill` | `999px` | 标签 `.tag`（全圆胶囊） |
| `radius_circle` | `50%` | 窗口按钮三圆点 |

### 3.2 控件基准高度（核心规律）

| 令牌 | 值 | 控件 |
| :--- | :--- | :--- |
| `control_h` | `32px` | **基准**：btn / select / input / tree-item / tab 均为 32px（min-height 或 height） |
| `control_h_send` | `30px` | 发送输入框 send-input |
| `control_h_console_tab` | `28px` | console-tab |
| `control_h_menu_item` | `25px` | 菜单栏 menu-item |
| `control_h_menu_popup` | `30px` | 菜单弹窗内按钮 |
| `row_table` | ~32px | 表格行（8px padding × 2 + 13px 文字 ≈ 32px，无显式行高） |
| `checkbox_size` | `14px` | 复选框 14×14 |

> **还原铁律**：基准控件高 32px 是整套设计的脊柱。PySide6 中给 QPushButton/QComboBox/QLineEdit 统一 `setFixedHeight(32)` 或 QSS `min-height:32px`。

### 3.3 间距（padding / gap 取值集合）

padding 横向常见值：`8px / 9px / 10px / 11px / 12px / 14px`；纵向由控件高度决定。gap 常见值：`2 / 4 / 5 / 6 / 7 / 8 / 9 / 10 / 12`。各区头 min-height：pane-title `38px`、card-head `36px`、console 第 1/3 行 `38px/42px`、modal-head `44px`、history-popover head `34px`。

---

## 4. 全局窗口网格

原型窗体是固定的 **5 行 grid**。这是高还原度的骨架，必须严格对齐。

### 4.1 网格定义

```text
.desktop-window {
  height: min(760px, calc(100vh - 36px));   /* 弹性高度 */
  min-height: 560px;
  border: 1px solid #9eabba;                /* color_window_border */
  border-radius: 8px;                        /* radius_lg */
  box-shadow: 0 18px 45px rgba(22,34,51,.18); /* shadow_window */
  display: grid;
  grid-template-rows: 34px 34px 50px minmax(0,1fr) 28px;
}
```

### 4.2 行布局图

```text
┌──────────────────────────────────────────────────────────┐
│ 标题栏 titlebar            高 34px  深底 #182231          │ 行1
├──────────────────────────────────────────────────────────┤
│ 菜单栏 menubar             高 34px  #f4f7fb               │ 行2
├──────────────────────────────────────────────────────────┤
│ 工具栏 toolbar             高 50px  #edf2f7               │ 行3
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 工作区 workspace           弹性 1fr  #e5ebf2             │ 行4
│   ├─ 侧边栏 sidebar  固定 230px（≤1050px 收 210px）       │
│   └─ 主区 main-area  弹性 1fr                            │
│        ├─ 标签栏 tabs    38px                            │
│        └─ 内容 content   弹性，可滚动                     │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ 状态栏 statusbar           高 28px  #eef2f7              │ 行5
└──────────────────────────────────────────────────────────┘
```

### 4.3 PySide6 还原策略

用 `QGridLayout` 作为顶层容器：

- 第 0 行（标题栏）/ 第 1 行（菜单栏）/ 第 2 行（工具栏）/ 第 4 行（状态栏）：`setRowStretch(n, 0)`，固定高度 34/34/50/28。
- 第 3 行（工作区）：`setRowStretch(3, 1)`，吃掉所有剩余空间。
- 工作区内部再用 `QHBoxLayout`：左 `QFrame(sidebar)` 固定宽 230（或 210），右 `main-area` 弹性。
- 窗口整体：`setMinimumSize(...)` 保证 ≥560 高，默认高度按 760 或视口动态计算。

### 4.4 响应式断点

原型仅一个断点 `max-width: 1050px`，影响：shell padding `18→10`、窗体高度公式 `calc(100vh - 36px) → calc(100vh - 20px)`、sidebar 列宽 `230→210`、modal-body 由两列变单列、toolbar 可横向滚动。

> PySide6 桌面应用通常不做响应式，但若需适配小屏工控机，可监听 `resizeEvent` 在宽度 ≤1050 时切换 sidebar 宽度。

---

## 5. 状态色体系

状态色不是孤立的色值，而是"业务状态 → 颜色 + 标签类 + 文案"的固定映射。还原时三者必须同时出现。

| 业务状态 | 颜色 | CSS 实现方式 | 典型文案 |
| :--- | :--- | :--- | :--- |
| 在线 / 正常 / OK | 绿 `color_ok` | `.stat-ok{color:var(--ok)}` / `.tag.ok`（底 `#e8f6ef`） | "在线" "COM3 已连接" "3 在线" |
| 告警 / 未确认 / 未保存 | 橙 `color_warn` | **无专用类**，原型用内联 `style="color:var(--warn)"` / `.tag.warn`（底 `#fff4df`） | "告警" "未确认" "1 未确认" "未保存" |
| 离线 | 默认文本色 | 纯文本，无颜色类（用 `color_text`） | "离线" |
| 危险 / 删除 | 红 `color_danger` | `.btn.danger`（底 `--danger`，边 `#9f2632`） / history-delete hover | "删除勾选" 删除图标 hover |
| 中性标签 | 灰 | `.tag`（底 `#e8edf4`，字 `#46566a`） | "COM3" "4 点" "v0.1" "CSV" |
| 选中（蓝系） | `color_primary` | 树/标签/表格选中：底 `#e9f4ff` + 字 `--primary` + 边框各档 | active 态 |
| 禁用 | 灰 | 边 `#c5ced8` 底 `#e5eaf0` 字 `#7b8795` | disabled 控件 |

> **重要还原规律**：
>
> 1. **告警态没有专用 CSS 类**，原型靠内联 `style="color:var(--warn)"`。PySide6 中应建模为业务模型字段（如 `Alarm.status == "unacknowledged"`）→ 在委托里设 `.setForeground(color_warn)`，不要靠内联样式。
> 2. **离线态无颜色**，是默认文本色——不要误把离线也涂成红/橙。
> 3. 已确认报警行：checkbox 永久 `disabled`，状态文字回退默认色，确认信息列写入"工程师 HH:MM:SS"。详见 [交互规范](interaction-spec.md) 报警确认状态机。

---

## 6. 还原总则（高还原度铁律）

下面是从原型提炼的全站一致性规律，PySide6 重写时必须遵守，否则会偏离设计：

1. **基准控件高 32px**：btn/select/input/tree-item/tab 统一 32px，是脊柱。
2. **字重无 normal**：所有可读文字至少 700；正文 700，强调 800，数值/标题 900。
3. **字号仅 5 档**：11/12/13/14/24px，不引入中间值。
4. **圆角仅 5 档**：输入与按钮 5px、卡片 6px、窗体与模态 8px、标签胶囊 999px。
5. **边框仅 1px**，且只有三档颜色：`color_line`（浅）/ `color_line_dark`（深）/ `color_window_border`（外框）。选中态另有三档蓝。
6. **阴影全站唯一**：`shadow_window` 一个值，用于所有浮层（窗体、菜单弹窗、popover、模态、toast）。
7. **配色克制**：语义色仅 绿/橙/红/蓝 四类 + 中性灰，禁止额外色相。
8. **等宽字仅用于数据**：终端、发送框、历史项、Markdown 输出用 `font_mono`，其余一律 `font_sans`。
9. **窗体网格固定 5 行**：34/34/50/1fr/28，前 3 行与末行像素固定，工作区吃剩余空间。
10. **数值大字**：metric-value 24px / weight 900，单位用 `<small>` 13px / muted 色。

---

## 7. 与原型的偏差处理

当 PySide6 实现与原型产生不可避免的偏差时（如原生控件渲染差异），遵循：

1. **数值优先**：颜色、尺寸、字号以本规范令牌为准，不以浏览器渲染截图为准。
2. **结构优先**：网格行高、控件层级以本规范为准。
3. **记录偏差**：实现中遇到无法 1:1 还原的控件（如 QComboBox 下拉箭头样式、QCheckBox 勾形），在控件映射规范里记录"近似方案"与"偏差说明"。
4. **不擅自美化**：不因为"Qt 默认更好看"而改动设计令牌。

---

## 8. 版本与维护

- 规范来源：原型 `assets/hmi/`。原型为模块化工程，入口为 `assets/hmi/index.html`，设计令牌位于 `assets/hmi/css/tokens.css`。（早期单文件原型已删除，模块化版功能完整且通过 jsdom 集成测试。）
- 本规范的所有数值（颜色、字号、间距、网格）与 `tokens.css` 一一对应，是 PySide6 重写的真相源。
- 若原型令牌变动（修改 `tokens.css`），本文件第 1 节令牌表必须同步更新。
- 强制同步：根据 `AGENTS.md` 第 9 节，原型与规范的任何变化必须同步更新本文件与其余三份。
