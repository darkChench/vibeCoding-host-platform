<!-- markdownlint-disable MD013 MD033 -->
# 控件映射规范 · HTML/CSS → PySide6 → QSS

> 用途：把原型每个原子控件，以三列表格给出 **HTML/CSS 定义 → PySide6 控件选型 → 可用 QSS 片段**，让 Qt 重写时控件选型与样式零歧义。
>
> 配套：先读 [总则与设计令牌](ui-restoration-spec.md) 掌握令牌名（本文 QSS 直接用令牌值）。

## 阅读约定

- QSS 中颜色直接填色值（QSS 不支持 CSS 变量）；若用 Python 主题，可把色值集中成常量后字符串拼接。
- "偏差说明"记录 PySide6 原生控件无法 1:1 还原之处及近似方案。
- 所有 QSS 片段假设已 `setObjectName` 或用属性选择器区分变体。

---

## 1. 按钮 QPushButton

**HTML/CSS 定义**：`.btn`（主） / `.btn.secondary`（次） / `.btn.danger`（危险） / `.btn:disabled`。
`min-height:32px; padding:0 11px; border-radius:5px; font-size:13px; font-weight:800;` 主色底 `--primary` + 边 `--primary-dark`；次级白底 + 边 `--line-dark`；危险底 `--danger` + 边 `#9f2632`。

| PySide6 控件 | QSS |
| :--- | :--- |
| `QPushButton` + `property("variant","primary/secondary/danger")` | 见下 |

```qss
QPushButton {
  min-height: 32px; padding: 0 11px;
  border: 1px solid #07588e; border-radius: 5px;
  background: #0b6fb3; color: #ffffff;
  font-size: 13px; font-weight: 800;
}
QPushButton:hover { background: #07588e; }
QPushButton[variant="secondary"] {
  border-color: #aeb9c8; background: #ffffff; color: #17202c;
}
QPushButton[variant="secondary"]:hover { background: #eef3f8; }
QPushButton[variant="danger"] {
  border-color: #9f2632; background: #bf3a46; color: #ffffff;
}
QPushButton:disabled {
  border-color: #c5ced8; background: #e5eaf0; color: #7b8795;
}
```

**偏差说明**：QSS `font-weight` 对 `QFont::Black(900)` 支持有限，`800` 通常已渲染为粗体，可接受。

---

## 2. 输入框 QLineEdit / QComboBox

**HTML/CSS 定义**：`.select`（下拉）/ `.input`（文本）/ `.send-input`（终端发送）。
`.select,.input { height:32px; padding:0 9px; border-radius:5px; border:1px solid #aeb9c8; background:#fff; font-size:13px; font-weight:700; }` `.select{min-width:100px}` `.select-compact{min-width:80px}` `.input.short{width:86px;text-align:center}`。send-input `height:30px; font: Consolas 等宽; font-weight:800`。

| PySide6 控件 | QSS |
| :--- | :--- |
| `.input` → `QLineEdit`；`.select` → `QComboBox`；`.send-input` → `QLineEdit`（设等宽字体） | 见下 |

```qss
QLineEdit {
  height: 32px; padding: 0 9px;
  border: 1px solid #aeb9c8; border-radius: 5px;
  background: #ffffff; color: #17202c;
  font-size: 13px; font-weight: 700;
}
QLineEdit:focus { border-color: #0b6fb3; }

QComboBox {
  min-width: 100px; height: 32px; padding: 0 9px;
  border: 1px solid #aeb9c8; border-radius: 5px;
  background: #ffffff; color: #17202c;
  font-size: 13px; font-weight: 700;
}
/* 紧凑变体用 property */
QComboBox[compact="true"] { min-width: 80px; }
QComboBox::drop-down { border: 0; width: 22px; }
QComboBox QAbstractItemView {
  border: 1px solid #aeb9c8; border-radius: 6px;
  background: #ffffff; selection-background-color: #e9f4ff;
  selection-color: #0b6fb3; padding: 4px;
}
QComboBox QAbstractItemView::item { min-height: 30px; padding: 0 10px; }
```

**偏差说明**：

- QComboBox 下拉箭头原生样式无法用纯 QSS 完美还原，可用 `setStyleSheet` 隐藏默认箭头 + 自绘 `QToolButton`，或接受 Qt 默认箭头。
- `.input.short` 居中：`QLineEdit[short="true"]{ qproperty-alignment: AlignCenter; max-width: 86px; }`。

### 2.1 自定义下拉（serial 页专用，替代原生 select）

**为什么需要**：serial 页 sendbar 的"发送格式"和"行结束符"原是原生 `<select>`。原生 select 弹出方向由浏览器决定（项数少向下弹、项数多向上弹），导致两个下拉方向不一致。原型用自定义组件 `.select-custom` 替代，**强制统一向上弹出**。

**HTML/CSS 定义**：`.select-custom`（容器，32px 高，5px 圆角，外观同 `.select`，带 `data-drop="up|down"` 属性控制弹出方向，`data-multi="true"` 启用多选）+ `.select-custom-value`（当前值/汇总）+ `.select-custom-caret`（▾ 箭头）+ `.select-custom-popup`（弹出层，`position:absolute`）+ `.select-custom-option`（选项，hover/selected 用 `#e9f4ff` + `--primary`；多选时前置 `.select-custom-check` 勾选标记 ✓）。
组件实现：`assets/hmi/js/components/dropdown.js`，API 为 `HMI.dropdown.html(name, items, selected, label, drop, opts)` / `.bind(root)` / `.getValue(root, name)` / `.onChange(name, cb)`。

- 单选：点击选项关闭弹层，onChange 回调值为 string。
- **多选**（`opts.multi:true`）：点击选项切换勾选、不关闭弹层，触发器显示已选汇总（`item.join("、")`），onChange 回调值为 string[]。当前用于历史数据页点位选择。

**弹出方向（重要）**：`drop` 参数取 `up`（默认，向上弹）或 `down`（向下弹）。

- `up`：popup 用 `bottom: calc(100% + 4px)` 定位在控件上方，箭头展开时翻转朝上。
- `down`：popup 用 `top: calc(100% + 4px)` 定位在控件下方，箭头始终朝下。
- **选方向的原则**：按下拉所在位置选空间充足的方向，避免被祖先容器（如 `.card` 的 `overflow:hidden`）裁切。当前用法：serial 页 sendbar 两个下拉用 `up`（上方终端区空间足）；params 页筛选下拉用 `down`（下方表格区空间足，且上方紧贴 card-head 会被裁切）。

| PySide6 控件 | 说明 |
| :--- | :--- |
| **直接用 `QComboBox`** | Qt 的下拉方向由 view position 控制，可自由设定，无浏览器那种限制。原型这个自定义组件**仅为统一 Web 视觉**，Qt 实现无需复刻，直接用原生 QComboBox 即可。 |

```qss
/* Qt 实现按普通 QComboBox 处理（见第 2 节 QSS），无需额外样式 */
```

**偏差说明**：Web 原型用自定义下拉是**平台限制的 workaround**，PySide6 重写时不要照搬这个组件——直接用 QComboBox，通过 `view->move()` 或样式表控制弹出位置即可。原型的 `.select-custom` 仅作为"这两个字段是下拉、选项是什么、默认值是什么"的需求参考。

---

## 3. 表格 QTableWidget

**HTML/CSS 定义**：`.table`（普通）/ `.param-table`（参数）/ `.alarm-table`（报警）。
`th` 背景 `#f1f5f9` 字 `#405066` weight 800；`td` padding 8px 下边框 `1px var(--line)`；行 hover 底 `#f8fbff`；选中行底 `#e9f4ff` + 内描边 `inset 0 0 0 1px #b7d8f2`。普通表 `tbody tr cursor:pointer`，param/alarm 表 `cursor:default`。`.select-cell{width:34px;text-align:center}` 内 checkbox 14×14。

| PySide6 控件 | QSS |
| :--- | :--- |
| `QTableWidget` + `QHeaderView`；首列 checkbox 用 `setCellWidget(row,0,QCheckBox)` 居中容器 | 见下 |

```qss
QTableWidget {
  border: 1px solid #cfd8e3; border-radius: 6px;
  background: #ffffff; gridline-color: #cfd8e3;
  font-size: 13px; font-weight: 700;
  selection-background-color: #e9f4ff;
  selection-color: #17202c;
}
QTableWidget::item { padding: 8px; border-bottom: 1px solid #cfd8e3; }
QTableWidget::item:hover { background: #f8fbff; }
QTableWidget::item:selected {
  background: #e9f4ff; border: 1px solid #b7d8f2;
}
QHeaderView::section {
  background: #f1f5f9; color: #405066;
  font-weight: 800; padding: 8px;
  border: 0; border-bottom: 1px solid #cfd8e3;
}
```

**偏差说明**：

- 表格行内描边 `inset box-shadow` QSS 不支持，用 `selection-border` 近似（`border:1px solid #b7d8f2`），或自定义 `QItemDelegate` 绘制。
- "普通表行可点击选中、param/alarm 表行不可选"：用 `setSelectionBehavior(SelectRows)` + `setSelectionMode(SingleSelection)` 对普通表；param/alarm 表 `setSelectionMode(NoSelection)`，仅靠首列 checkbox 表达选择。
- checkbox 列：用 `setCellWidget` 放居中 QCheckBox，不用 `Qt::ItemIsUserCheckable`（后者勾在文字左侧无法居中）。

---

## 4. 树导航 QListWidget

**HTML/CSS 定义**：`.tree-item`。
`min-height:32px; padding:0 8px; border-radius:5px; border:1px transparent;` 内部 grid `18px 1fr auto` gap 7px（图标 / 文字 / 标签）。hover：边 `--line` 底 `#fff`；active：边 `#9bc6e8` 底 `#e9f4ff` 字 `--primary`。配 `.tag` 标签（数量/状态）。`.tree-heading` muted 色 12px 大写小标题。

| PySide6 控件 | QSS |
| :--- | :--- |
| `QListWidget`（每项自定义 `QWidget`：图标 + 文字 + tag）；或 `QTreeWidget` 单层 | 见下 |

```qss
QListWidget {
  background: transparent; border: 0; padding: 10px;
}
QListWidget::item {
  min-height: 32px; padding: 0 8px; margin: 1px 0;
  border: 1px solid transparent; border-radius: 5px;
  color: #17202c; font-size: 13px; font-weight: 700;
}
QListWidget::item:hover { border-color: #cfd8e3; background: #ffffff; }
QListWidget::item:selected {
  border-color: #9bc6e8; background: #e9f4ff; color: #0b6fb3;
}
```

**偏差说明**：

- 原型 tree-item 内是"图标 + 文字 + 右侧 tag"三列，纯 `QListWidget::item` 文本无法承载。**推荐**用 `setItemWidget(row, customWidget)`，customWidget 是 `QHBoxLayout`（icon QLabel + text QLabel + stretch + tag QLabel）。QSS 只控外框，内部用调色板。
- `.tree-heading`（"设备"/"数据"/"工具"小标题）用不可选的 `QListWidgetItem` + `setItemWidget` 一个 muted QLabel，或直接在 list 外用 QLabel 分组。

---

## 5. 标签页 QTabWidget

原型有两套 tab：

- 主区 `.tab`：`min-height:32px; padding:0 12px; border-radius:6px 6px 0 0`，默认底 `#edf2f7` 字 `#35465a`；active 底 `#fff` 字 `--primary` 边 `#b9cce0`。
- 控制台 `.console-tab`：`min-height:28px; padding:0 9px; border-radius:5px; font-size:12px`，active 边 `--primary` 底 `#e9f4ff` 字 `--primary`。

| PySide6 控件 | QSS |
| :--- | :--- |
| 主区 → `QTabWidget`（文档窗口风格）；控制台 → `QTabWidget`（圆角按钮风格） | 见下 |

```qss
/* 主区 tab —— 文档窗口样式 */
QTabWidget::pane { border: 0; background: #ffffff; }
QTabBar::tab {
  min-height: 32px; padding: 0 12px;
  border: 1px solid #b9cce0; border-bottom: 0;
  border-top-left-radius: 6px; border-top-right-radius: 6px;
  background: #edf2f7; color: #35465a;
  font-size: 13px; font-weight: 800; margin-right: 2px;
}
QTabBar::tab:selected { background: #ffffff; color: #0b6fb3; }

/* 控制台 tab —— 圆角按钮样式（用 objectName 区分） */
QTabBar[variant="console"]::tab {
  min-height: 28px; padding: 0 9px;
  border: 1px solid #cfd8e3; border-radius: 5px;
  background: #ffffff; color: #344457;
  font-size: 12px; font-weight: 800; margin-right: 6px;
}
QTabBar[variant="console"]::tab:selected {
  border-color: #0b6fb3; background: #e9f4ff; color: #0b6fb3;
}
```

**偏差说明**：原型 tab 是可关闭/动态增减的（PRD 新增页会加 tab），QTabWidget 原生支持 `setTabsClosable`，与原型行为一致。

---

## 6. 卡片 QFrame 组合

**HTML/CSS 定义**：`.card`（1px 边 `--line`，圆角 6px，白底）+ `.card-head`（min-height 36px，底 `#f7f9fc`，下边框 `--line`，flex 两端对齐：标题 + tag）+ `.card-body`（padding 10px）。
`.metric`（min-height 78px，底 `#f8fafc`，1px 边，圆角 6px）：label 12px muted 800 + value 24px weight 900（单位 `<small>` 13px muted）。
`.quick-card`（min-height 72px，hover 边 `--primary` 底 `#e9f4ff`）：左 `.quick-icon` 34×34 圆角 6px 主色底白字 + 右标题 900 + 描述 12px muted。

| PySide6 控件 | QSS |
| :--- | :--- |
| `QFrame`（设 `frameShape=NoFrame`）容器 + 内部 `QVBoxLayout`：head（QLabel + tag）+ body | 见下 |

```qss
QFrame[role="card"] {
  border: 1px solid #cfd8e3; border-radius: 6px; background: #ffffff;
}
QFrame[role="card-head"] {
  min-height: 36px; background: #f7f9fc;
  border-bottom: 1px solid #cfd8e3; font-weight: 800;
}
QFrame[role="card-body"] { padding: 10px; } /* QSS padding 对 QFrame 部分生效，建议布局留白 */

QFrame[role="metric"] {
  min-height: 78px; border: 1px solid #cfd8e3;
  border-radius: 6px; background: #f8fafc; padding: 10px;
}
QLabel[role="metric-label"] { color: #617083; font-size: 12px; font-weight: 800; }
QLabel[role="metric-value"] { font-size: 24px; font-weight: 900; }

QFrame[role="quick-card"] {
  min-height: 72px; border: 1px solid #cfd8e3; border-radius: 6px;
  background: #f8fafc; padding: 10px;
}
QFrame[role="quick-card"]:hover { border-color: #0b6fb3; background: #e9f4ff; }
QLabel[role="quick-icon"] {
  min-width: 34px; min-height: 34px; border-radius: 6px;
  background: #0b6fb3; color: #ffffff; font-weight: 900;
  qproperty-alignment: AlignCenter;
}
```

**偏差说明**：QSS 的 `padding` 对 `QFrame` 仅在少数子控件生效，card-body 的 10px 内边距**推荐用布局 `setContentsMargins(10,10,10,10)` 实现**，而非依赖 QSS。

---

## 7. 图表

**HTML/CSS 定义**：`.chart`（height 180px，圆角 6px，1px 边 `--line`，背景含 30px/80px 重复网格线 `#e1e8f0` + `#fbfdff`），内嵌 SVG 双折线（主色 `#0b6fb3` 4px + 绿 `#11875d` 3px）。

| PySide6 控件 | 方案 |
| :--- | :--- |
| **方案 A**：`QChartView`（QtCharts），折线 `QLineSeries`，背景画网格 | 原生、轻量，但样式需手调 |
| **方案 B**：`QWebEngineView` 嵌 ECharts/Chart.js | 还原度最高（与原型同源），但引入 Chromium |

**还原建议**：第二阶段原型将用 Chart.js（Web 端）。若 PySide6 选方案 B，可几乎直接复用；若选方案 A，需手动配：

- 背景 `#fbfdff`，网格线 `#e1e8f0`（横线间隔 ~30px、竖线 ~80px 像素映射）。
- 主曲线 `QPen(QColor("#0b6fb3"), 4)`；副曲线 `QPen(QColor("#11875d"), 3)`。
- 高度 180px，外框 1px `#cfd8e3` + 圆角 6px。

**偏差说明**：QtCharts 默认轴/网格样式与原型差异较大，需关掉默认装饰、手绘背景网格才能高还原。监控页曲线需实时刷新，方案 A 性能更好。

---

## 8. 复选框 QCheckBox

**HTML/CSS 定义**：原生 `input[type=checkbox]`，`14×14`，`accent-color: var(--primary)`。`.check-label` 行内排布（checkbox + 文字，gap 5px，高 30px，12px 800）。

| PySide6 控件 | QSS |
| :--- | :--- |
| `QCheckBox`；勾形/方框 QSS 支持有限 | 见下 |

```qss
QCheckBox { spacing: 5px; color: #344457; font-size: 12px; font-weight: 800; }
QCheckBox::indicator {
  width: 14px; height: 14px;
  border: 1px solid #aeb9c8; border-radius: 3px; background: #ffffff;
}
QCheckBox::indicator:checked {
  background: #0b6fb3; border-color: #0b6fb3;
  image: url(:/icons/check-white.svg); /* 需自备白色对勾资源 */
}
```

**偏差说明**：QSS 无法设 `accent-color`，勾选后是 Qt 默认对勾。**高还原做法**：自备白色对勾 SVG/PNG 作为 `image`，或继承 `QCheckBox` 重绘 `paintEvent`。已确认报警行的 checkbox 需 `setEnabled(false)`，禁用态自动用 `color_disabled_*`。

---

## 9. 终端 QPlainTextEdit

**HTML/CSS 定义**：`.terminal`（暗底 `#101a27`，字 `#dceafe`，等宽 12px，行高 1.55，padding `8px 10px`，可滚动）。每行 `.terminal-line` 是 grid `36px 74px 1fr`：列 1 方向标签（`.rx` `#7dd3fc` / `.tx` `#86efac`，weight 800）+ 列 2 时间/累计 + 列 3 内容。

| PySide6 控件 | QSS |
| :--- | :--- |
| **方案 A**：`QPlainTextEdit`（只读，appendPlainText 按行追加，用 HTML 富文本上色）→ 推荐 | 方案 A 见下 |
| **方案 B**：`QTableWidget` 三列（方向/时间/内容），列宽固定 36/74/弹性 | 表格样式参考第 3 节 |

```qss
QPlainTextEdit[role="terminal"] {
  background: #101a27; color: #dceafe;
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px; padding: 8px 10px;
  border: 0; border-radius: 0;
}
```

**还原建议**（方案 A）：

- 用 `appendHtml()` 追加每行，富文本内联色：RX 行 `<span style="color:#7dd3fc">RX</span>`，TX 行 `<span style="color:#86efac">TX</span>`。
- 列对齐用等宽字体 + 固定宽度占位（如方向标签固定 2 字符宽，时间固定 8 字符），或用制表符/空格补齐——原生 QPlainTextEdit 不支持三列网格，方案 B 表格更整齐。

**偏差说明**：若要严格三列对齐，**方案 B（QTableWidget）还原度更高**，代价是滚动/选择行为要单独处理。

---

## 10. 模态/弹层 QDialog / QFrame

原型有五类浮层：

| 原型类 | 用途 | PySide6 | QSS 要点 |
| :--- | :--- | :--- | :--- |
| `.modal`（1080px）/ `.modal-backdrop` | PRD 编辑器 | `QDialog`（模态）+ 自绘遮罩 | 宽 `min(1080px,100%)`，44px head，圆角 8px，阴影 `shadow_window`，遮罩 `rgba(15,23,42,.42)` |
| `.action-modal`（460px） | 通用操作确认 | `QDialog`（模态） | 460px，head + action-body（14px）+ footer，圆角 8px |
| `.menu-popup` | 菜单栏下拉 | `QMenu` | min-width 178px，圆角 6px，padding 5px，项 min-height 30px hover 底 `#e9f4ff` 字 `--primary` |
| `.history-popover`（560px/260h） | 发送历史 | `QFrame`（绝对定位浮层）或 `QMenu` 自定义 | 定位：left 10px、bottom 46px（相对 console） |
| `.toast` | 操作反馈 | `QFrame`（无边框，定时隐藏） | 右下 20px，圆角 8px，底 `#17202c` 白字 14px |

```qss
/* QMenu —— 菜单弹窗 */
QMenu {
  min-width: 178px; border: 1px solid #aeb9c8; border-radius: 6px;
  background: #ffffff; padding: 5px;
}
QMenu::item { min-height: 30px; padding: 0 10px; border-radius: 4px; }
QMenu::item:selected { background: #e9f4ff; color: #0b6fb3; }

/* QDialog 模态 */
QDialog { border: 1px solid #9eabba; border-radius: 8px; background: #ffffff; }
```

**偏差说明**：

- 模态遮罩：QDialog 模态自带半透明遮罩但颜色不可控，需 `setWindowOpacity` 或自绘 `QFrame` 全屏遮罩层近似 `rgba(15,23,42,.42)`。
- 圆角 8px 在 QDialog 上需 `setWindowFlags(Qt::FramelessWindowHint)` + `setAttribute(Qt::WA_TranslucentBackground)` 才生效。
- Toast 用 `QFrame` + `QTimer::singleShot(1600ms, hide)`，定位 `move(parent.width()-190, parent.height()-60)`。

---

## 11. 工具栏 / 状态栏 / 标题栏 / 菜单栏

**HTML/CSS 定义**：

- `.titlebar`：grid `auto 1fr auto`，gap 12，深底 `#182231` 白字，34px。左 app-mark（图标 + 名，800）+ 中居中副标题（`#d6e2ef` 13px）+ 右三圆点。
- `.menubar`：flex gap 4，底 `#f4f7fb`，34px。`.menu-item` min-height 25px 圆角 4 hover 底白边 `--line`。
- `.toolbar`：10 列 grid（前 8 列 + 弹性 + 末列），gap 8，padding `8px 10px`，底 `#edf2f7`，50px。`.tool-group`（label + select）+ `.stats-strip`（右对齐统计）。
- `.statusbar`：flex 两端，padding `0 10px`，顶边 `--line-dark`，底 `#eef2f7` 字 `#405066` 12px 700，28px。

| PySide6 控件 | QSS |
| :--- | :--- |
| titlebar/menubar/toolbar/statusbar 均用 `QFrame` + 内部布局；菜单项 `QPushButton[flat]` 或 `QToolButton` | 见下 |

```qss
QFrame[role="titlebar"] { background: #182231; color: #ffffff; min-height: 34px; }
QFrame[role="menubar"] { background: #f4f7fb; color: #293648; min-height: 34px; }
QPushButton[role="menu-item"] {
  min-height: 25px; padding: 0 10px; border-radius: 4px;
  border: 1px solid transparent; background: transparent;
  color: #293648; font-size: 13px; font-weight: 700;
}
QPushButton[role="menu-item"]:hover { border-color: #cfd8e3; background: #ffffff; }
QFrame[role="toolbar"] { background: #edf2f7; min-height: 50px; }
QFrame[role="statusbar"] {
  background: #eef2f7; color: #405066;
  border-top: 1px solid #aeb9c8; min-height: 28px;
  font-size: 12px; font-weight: 700;
}
```

**偏差说明**：窗口三圆点（min/max/close）原生用 `QWindow` 系统按钮即可，颜色不可控但行为一致；若必须还原三色圆点，需 `FramelessWindowHint` 自绘标题栏。

> **AI 状态指示（`.stat-warn`）**：工具栏右侧 stats-strip 增加 AI 状态指示项。已配置模型→`.stat-ok`（绿）"AI 就绪"；未配置→`.stat-warn`（警告色 `--warn`）"AI 未配置"。`.stat-warn` 复用 `.tag.warn` 的 `--warn` 色（`#b86b00` 文字 / `#fff4df` 底），在 PySide6 中可用 `QLabel[role="stat"][variant="warn"]`，QSS 同第 12 节 tag.warn。

---

## 12. 标签 tag

**HTML/CSS 定义**：`.tag`（胶囊 `999px`，padding `2px 7px`，11px 800，底 `#e8edf4` 字 `#46566a`）+ `.tag.ok`（底 `#e8f6ef` 字 `--ok`）+ `.tag.warn`（底 `#fff4df` 字 `--warn`）。无 `.tag.danger`。

| PySide6 控件 | QSS |
| :--- | :--- |
| `QLabel`（小胶囊）+ `property("variant","ok/warn/none")` | 见下 |

```qss
QLabel[role="tag"] {
  border-radius: 999px; padding: 2px 7px;
  background: #e8edf4; color: #46566a;
  font-size: 11px; font-weight: 800;
}
QLabel[role="tag"][variant="ok"] { background: #e8f6ef; color: #11875d; }
QLabel[role="tag"][variant="warn"] { background: #fff4df; color: #b86b00; }
```

---

## 13. 表单字段

**HTML/CSS 定义**：`.field`（label + input 垂直 gap 4）+ `.form-grid`（2 列 gap 10）。label 12px muted 800。

| PySide6 控件 | QSS |
| :--- | :--- |
| `QWidget` 容器 + `QFormLayout` 或 `QGridLayout`（label QLabel + field 控件） | label 用 QLabel[role="field-label"] |

```qss
QLabel[role="field-label"] { color: #617083; font-size: 12px; font-weight: 800; }
```

**偏差说明**：`.form-grid` 的 2 列等宽用 `QGridLayout` 列 stretch 均分；跨列字段（如"说明"）用 `addWidget(widget, row, 0, 1, 2)`。

---

## 14. 全局字体应用

```python
# PySide6 主入口
app = QApplication([])
font = QFont("Microsoft YaHei", 9)  # 9pt ≈ 12px，按实际校准
font.setWeight(QFont.Bold)
app.setFont(font)
```

> QSS 字号用 px 在高 DPI 下可能不随缩放，生产环境建议 pt 或启用 `AA_EnableHighDpiScaling`。详见 [总则 §7 偏差处理](ui-restoration-spec.md#7-与原型的偏差处理)。

---

## 15. AI 助手页组件（第二阶段新增）

> 渲染进 `#content` 的标准页面（不再是浮动侧栏）。布局见 [页面布局规范 §11](page-layout-spec.md)，行为见 [交互规范 §9](interaction-spec.md)。实现：`js/pages/aiAssistant.js`。

**HTML 结构**：单张大 `.card`（占满 content 区）+ 标准 `.card-head`（"✦AI 运维助手" + 模型配置状态 tag）+ `.card-body .ai-page-body`（三行 grid，`height: calc(100vh - 180px)`）+ `.ai-messages`（内含 `.ai-bubble-user` / `.ai-bubble-assistant` / `.ai-tool-card` / `.ai-thinking`）+ `.ai-input-wrap`（`.ai-input` + 发送按钮）+ `.ai-hint`。

> AI 页复用标准 `.card` / `.card-head`（见第 6 节卡片样式），**不单独需要 `.ai-head`**。

| 原型类 | PySide6 控件 | 说明 |
| :--- | :--- | :--- |
| `.ai-page` / `.ai-page-body` | `QFrame`（标准页面容器，三行 `QGridLayout`） | 整体 `height: calc(100vh - 180px)`，三行：消息区 `minmax(0,1fr)` / 输入区 / 提示行 |
| `.ai-messages` | `QScrollArea`（grid 行 `minmax(0,1fr)` 的滚动容器） | 固定高度由 `.ai-page` 的 `height: calc(100vh - 180px)` 控制，承载对话历史（`store.aiMessages`） |
| `.ai-bubble-user` | `QLabel` 放入 `QScrollArea`；或整体用 `QTextBrowser` | 右对齐，主色底白字。QTextBrowser 可承载富文本气泡序列 |
| `.ai-bubble-assistant` | `QLabel` 放入 `QScrollArea`；或 `QTextBrowser` | 左对齐，白底边框。多条气泡建议用 `QScrollArea` + 自定义 `QFrame` 列表，或 `QTextBrowser` 追加 HTML |
| `.ai-tool-card` | 自定义 `QFrame`（`setObjectName("ai-tool-card")`） | 含函数名 QLabel + 参数 QLabel + 状态标记 QLabel，按 running/done/error 切样式 |
| `.ai-thinking`（三点动画） | `QMovie` 加载 GIF；或自绘 `QTimer` 动画（三个 QLabel 依次显示跳动） | 等待 LLM/工具响应时显示。GIF 最省事；自绘需 `QTimer` 周期切换三个点透明度 |
| `.ai-input` | `QTextEdit` 或 `QPlainTextEdit` | 自适应高度，placeholder 用 `setPlaceholderText` |

**QSS 片段（气泡）**：

```qss
/* 用户气泡：主色底、白字、右下角直角 */
QFrame[role="ai-bubble-user"] {
  background: #0b6fb3; color: #ffffff;
  border-radius: 8px;
  border-bottom-right-radius: 2px;
  padding: 8px 11px; max-width: 280px;
}

/* 助手气泡：白底、灰边框、左下角直角 */
QFrame[role="ai-bubble-assistant"] {
  background: #ffffff; color: #17202c;
  border: 1px solid #cfd8e3; border-radius: 8px;
  border-bottom-left-radius: 2px;
  padding: 8px 11px; max-width: 280px;
}

/* 工具调用卡片：默认边框；error 转 warn 色 */
QFrame[role="ai-tool-card"] {
  background: #f8fafc; border: 1px solid #cfd8e3;
  border-radius: 6px; padding: 8px 11px;
}
QFrame[role="ai-tool-card"][state="error"] {
  border-color: #b86b00; background: #fff4df;
}
```

**偏差说明**：

- 气泡圆角 + 单角直角（用户右下、助手左下）：QSS 对 `QFrame` 的四角不同圆角支持有限，可用 `border-radius` 统一圆角近似，或自绘 `paintEvent` 精确还原。
- `max-width` 在 `QFrame` 上不约束自动布局宽度，需在布局中 `setMaximumWidth` 或用弹簧（`addStretch`）推到一侧实现左/右对齐。
- 思考动画三点：`QMovie` 最简单（需 GIF 资源）；无资源时可用 3 个 `QLabel` + `QTimer` 周期改变样式表模拟跳动。

---

## 16. 控件映射速查表

| 原型类 | PySide6 控件 | 关键尺寸 |
| :--- | :--- | :--- |
| `.btn` | QPushButton | 32px 高，5px 圆角 |
| `.input`/`.select`/`.send-input` | QLineEdit / QComboBox | 32px / 30px 高 |
| `.table` | QTableWidget | 行 ~32px，首列 checkbox widget |
| `.tree-item` | QListWidget + setItemWidget | 32px 高，三列自定义 widget |
| `.tab`/`.console-tab` | QTabWidget | 32px / 28px 高 |
| `.card`/`.metric`/`.quick-card` | QFrame 组合 | card-head 36px，metric 78px |
| `.chart` | QChartView 或 QWebEngineView | 180px 高 |
| checkbox | QCheckBox | 14×14，自绘对勾 |
| `.terminal` | QPlainTextEdit 或 QTableWidget | 三列对齐选表格 |
| `.modal`/`.action-modal` | QDialog | 1080 / 460px |
| `.menu-popup` | QMenu | min 178px |
| `.toast` | QFrame + QTimer | 1600ms |
| `.tag` | QLabel 胶囊 | 999px 圆角 |
| titlebar/menubar/toolbar/statusbar | QFrame | 34/34/50/28px |
| `.stat-warn` | QLabel（variant=warn） | 复用 tag.warn 色，AI 未配置状态 |
| `.ai-bubble-user/assistant` | QLabel / QTextBrowser | 8px 圆角，单角直角 |
| `.ai-tool-card` | 自定义 QFrame | 6px 圆角，error 转 warn 色 |
| `.ai-input` | QTextEdit / QPlainTextEdit | placeholder 提示 |

---

## 17. 版本与维护

- 规范来源：原型 CSS（行 7-1073）+ 第二阶段新增的 AI 助手侧栏样式。
- 第二阶段原型拆分后若 CSS 令牌变动，本文件 QSS 片段需同步。
- QSS 已尽量贴近原型色值；个别原生控件偏差已在"偏差说明"标注，实现时按标注处理。
