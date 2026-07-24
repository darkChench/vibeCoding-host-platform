<!-- markdownlint-disable MD013 MD033 -->
# 页面布局规范 · 页面逐一

> 用途：固化原型各页面的布局结构、区块/控件清单、数据字段与状态变体（含第二阶段新增的模型配置页与 AI 助手页），让 PySide6 重写时每页的网格划分与内容零歧义。
>
> 配套：控件样式见 [控件映射规范](widget-qss-spec.md)，交互行为见 [交互规范](interaction-spec.md)，令牌见 [总则](ui-restoration-spec.md)。

## 阅读约定

- 每页固定五段：**ASCII 布局图** / **区块清单** / **控件清单（含数值）** / **数据字段** / **状态变体**。
- 主区通用结构：顶部 tabs 行（38px）+ content 滚动区（padding 12px），content 内是各页内容。
- 所有页共用 `.grid`（gap 10）+ `.card`（6px 圆角）+ `.metric`（78px）等原子，详见控件规范。

---

## 通用主区容器（所有页面外层）

```text
main-area (QFrame, 弹性)
├─ tabs 行        高 38px   背景 #f7f9fc，下边框 --line
└─ content 区     弹性可滚  padding 12px，背景 #fff
     └─ <各页内容>
```

> tabs 显示 8 个页面标签 + 动态新增的 PRD 页；点击切换页面。详见交互规范"导航"。

---

## 1. 首页/总览 overview

### 1.1 布局图

```text
content (padding 12px)
┌───────────────────────────┬───────────────────────────┐
│ 卡片A 运行总览            │ 卡片B 快捷操作            │
│ card-head 36px            │ card-head 36px            │
│ ┌─────┬─────┬─────┐       │ ┌─────────┬─────────┐     │
│ │串口 │在线 │当前 │       │ │快捷:串口│快捷:监控│     │  grid cols-2
│ │COM3 │设备3│告警1│       │ ├─────────┼─────────┤     │  (等宽两列)
│ └─────┴─────┴─────┘       │ │快捷:报警│快捷:历史│     │
│ ┌───────────┐ (第4格)     │ └─────────┴─────────┘     │
│ │离线阈值10 │             │                           │
│ └───────────┘             │                           │
├───────────────────────────┴───────────────────────────┤
│ 卡片C 设备列表 (margin-top 10px)                       │
│ card-head 36px  右侧 tag "3 在线"                      │
│ 表格 7 列                                              │
└────────────────────────────────────────────────────────┘
```

### 1.2 区块清单

| 区块 | 结构 | 说明 |
| :--- | :--- | :--- |
| 卡片A 运行总览 | card + card-head（"运行总览" + tag.ok "在线"）+ card-body `.grid cols-3` 4 个 metric | metric 不满整行（4 个放 3 列，第 4 个占 1 格） |
| 卡片B 快捷操作 | card + card-head（"快捷操作" + tag "工作台"）+ card-body `.grid cols-2` 4 个 quick-card | quick-card 带 `data-jump` 跳转 |
| 卡片C 设备列表 | card（margin-top 10px）+ card-head（"设备列表" + tag.ok "3 在线"）+ card-body 单张 table | 普通表，行可点击选中 |

### 1.3 控件清单

- 4× `.metric`：当前串口 COM3 / 在线设备 3 / 当前告警 1 / 离线阈值 10<small>min</small>。
- 4× `.quick-card`：图标 ↔ "设备连接" / ▥ "实时监控" / ! "报警记录" / ◇ "历史数据"。
- 1× `.table`（7 列）：设备 / 设备地址 / 设备 ID / 状态 / 最后通讯 / 离线判定 / 告警。

### 1.4 数据字段（设备表）

| 列 | 示例值 | 状态色处理 |
| :--- | :--- | :--- |
| 设备 | F407-USB-UART / 温湿度终端 / 压力采集器 / 备用终端 | 默认 |
| 设备地址 | 01 / 02 / 03 / 04 | 默认 |
| 设备 ID | UART-001 / TH-002 / PRS-003 / BK-004 | 默认 |
| 状态 | 在线 / 在线 / 告警 / 离线 | 在线→`.stat-ok`；告警→内联 `--warn`；离线→默认色 |
| 最后通讯 | 28 ms 前 / 1.2 s 前 / 3.5 s 前 / 12 min 前 | 默认 |
| 离线判定 | < 10 min（前3行）/ >= 10 min（第4行） | 默认 |
| 告警 | 0 / 0 / 1 / 0 | 默认 |

### 1.5 状态变体

- 4 行预置：3 在线/告警（< 10 min）+ 1 离线（>= 10 min）。展示离线判定规则的对比效果。
- 行点击：选中该行（`.selected`），toast"已选中：{设备名}"。

---

## 2. 设备连接 serial

### 2.1 布局图

```text
content (padding 12px)
┌────────────────────────────────────────────────────────┐
│ serial-workbench (单行 grid)                           │
│ ┌────────────────────────────────────────────────────┐ │
│ │ console (38px / 1fr / 42px 三行)                   │ │
│ │ ┌──────────────────────────────────────────────┐   │ │
│ │ │ console-tabs 38px                            │   │ │
│ │ │ [串口原始日志][通信统计][诊断日志]  …  [✓时间戳]│   │ │
│ │ ├──────────────────────────────────────────────┤   │ │
│ │ │ terminal (暗底 #101a27，可滚动)              │   │ │
│ │ │   RX 14:28:32  01 03 08 ...                  │   │ │
│ │ │   TX 14:28:33  01 03 00 ...                  │   │ │
│ │ │   ...                                        │   │ │
│ │ │   ┌─ history-popover (浮层，默认隐藏) ──────┐│   │ │
│ │ │   │ 最近发送 20 条            [清空]        ││   │ │
│ │ │   │ 01 03 00 00 00 04            [x]        ││   │ │
│ │ │   │ ...                                     ││   │ │
│ │ │   └─────────────────────────────────────────┘│   │ │
│ │ ├──────────────────────────────────────────────┤   │ │
│ │ │ sendbar 42px                                │   │ │
│ │ │ [发送框      ][历史] [HEX▾] 行结束符[无▾]    │   │ │
│ │ │ [✓自动发送] [1000] ms            [发送]      │   │ │
│ │ └──────────────────────────────────────────────┘   │ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

### 2.2 区块清单

| 区块 | 结构 | 说明 |
| :--- | :--- | :--- |
| console-tabs | grid `auto auto auto 1fr auto`，38px | 3 个 console-tab + 弹性占位 + 时间戳 checkbox |
| terminal | 暗底可滚，padding `8px 10px` | 每行 terminal-line 三列 grid `36px 74px 1fr` |
| history-popover | 浮层，绝对定位 left 10 bottom 46 | 默认 `display:none`，`.open` 时 `34px / 1fr` 两行 |
| sendbar | grid `1fr auto auto auto auto auto auto auto`，42px | 8 列：发送框组 / 格式 / 行结束符 label+select / 自动发送 checkbox / 间隔 input / ms label / 发送按钮 |

### 2.3 控件清单

- 3× `.console-tab`（data-console = raw/stats/diagnostic，raw 默认 active）。
- `.terminal` + N× `.terminal-line`（每行：方向色类 + 时间/累计 + 内容）。
- `.history-popover`：head（标题 + `data-send-history-clear` 清空按钮）+ `.history-list`（每项：`history-pick` + `history-delete`）。
- sendbar 控件：`.send-input`（value "01 03 00 00 00 04"）+ `data-send-history-toggle` 历史 button + **发送格式自定义下拉**（HEX/ASCII，`.select-custom[data-dropdown-name="sendFormat"]`）+ **行结束符自定义下拉**（无/CR/LF/CRLF，`.select-custom[data-dropdown-name="lineEnding"]`）+ 自动发送 checkbox + 间隔 `.input.short`（number 1000）+ ms label + `data-send-action` 发送 button。
  - 格式与行结束符用自定义下拉（`js/components/dropdown.js`）而非原生 select，是为了**强制统一向上弹出**（原生 select 弹出方向由浏览器决定，项数不同会导致两个下拉一上一下不一致）。详见 [控件映射规范 §2.1](widget-qss-spec.md)。

### 2.4 数据字段（终端行）

| tab | 方向类 | 标签列 | 内容列 |
| :--- | :--- | :--- | :--- |
| raw | `.rx` / `.tx` | 时间 HH:MM:SS | HEX 帧 |
| stats | `.rx` / `.rx` OK / `.tx` CRC / `.rx` TIMEOUT | 累计 / 成功率 / 错误 / 超时 | 数值 |
| diagnostic | `.rx` / `.tx`（INFO/WARN） | 时间 | 日志文本 |

发送历史：localStorage key `multi-protocol-hmi-send-history`，最多 20 条，去重置顶。默认 4 条：`01 03 00 00 00 04` / `01 06 00 10 00 01` / `01 03 00 04 00 02` / `01 10 00 20 00 02 04 00 64 00 C8`。

### 2.5 状态变体

- **未连接态（第二阶段补）**：terminal 提示"串口未连接"，发送按钮 disabled 或点击提示连接。
- **空历史**：popover 列表显示 `.history-empty` "暂无发送历史"。
- **HEX/ASCII 切换（第二阶段补）**：影响发送框内容解析与 terminal 显示格式。

---

## 3. 实时监控 monitor

### 3.1 布局图

```text
content (padding 12px)
┌────────────────────────────────────────────────────────┐
│ 卡片A 实时点位 (grid 单列，垂直堆叠两张卡)             │
│ card-head "实时点位" + tag.ok "运行"                    │
│ ┌───────────────────┬───────────────────┐              │
│ │温度 25.0 ℃        │压力 30.0 MPa      │  grid cols-2 │
│ ├───────────────────┼───────────────────┤              │
│ │密度 5.00 MPa      │流量 1.00 L/min    │              │
│ └───────────────────┴───────────────────┘              │
├────────────────────────────────────────────────────────┤
│ 卡片B 短周期趋势                                        │
│ card-head "短周期趋势" + tag "最近 10 分钟"             │
│ chart (180px，双折线)                                   │
└────────────────────────────────────────────────────────┘
```

### 3.2 区块清单

| 区块 | 结构 |
| :--- | :--- |
| 卡片A 实时点位 | card + card-head + card-body `.grid cols-2` 4 个 metric |
| 卡片B 短周期趋势 | card + card-head + card-body 内 `chartHtml()` |

### 3.3 控件清单

- N× `.metric`（数量动态）：**来自参数配置页 `category="采样参数"` 的条目**，每项显示 `display` 名 + 当前值 + `unit` 单位。原型阶段值在参数 `min/max` 范围内随机生成，每 1s 刷新。
- 趋势曲线 card-head：标题"短周期趋势" + **曲线筛选 chip 列表**（每个采样参数一个 `.curve-chip`，带颜色圆点 + 显示名，点击切换该曲线显示/隐藏）。chip 颜色对应曲线颜色，隐藏态淡化 + 删除线。
- 1× `.chart`（180px）：**曲线数量 = 启用显示的采样参数数量**（受 chip 控制），颜色按调色板分配（主色蓝 #0b6fb3、绿 #11875d、橙/红/灰循环，按采样参数在完整列表中的索引固定，不随显隐变化），Chart.js 渲染，每 1s 追加新点滚动。

> 数据联动：metric 点位与趋势曲线都读取 `store.params` 的采样参数，在参数配置页增删采样参数后，本页 chip 与曲线自动跟随。配置参数（category="配置参数"）不参与本页。
>
> 曲线显隐：chip 点击切换 `store.curveVisible[paramName]`（默认全部 true），曲线只画启用集。全部隐藏时图表区显示空态"所有曲线已隐藏，点击上方标签显示"。

### 3.4 数据字段

每个 metric 卡对应一个采样参数（来自 params 模型）：

| 字段 | 来源 | 说明 |
| :--- | :--- | :--- |
| 标签 | `param.display`（无则 `param.name`） | 显示名 |
| 数值 | `min/max` 范围内随机（原型阶段） | 真实设备接入后改为 Modbus 读值 |
| 单位 | `param.unit` | 紧贴数值，`<small>` 字号 |
| 小数位 | `param.decimals` | 决定 `toFixed` 精度 |

### 3.5 状态变体

- **无采样参数**：metric 区与图表区显示空态"暂无采样参数（请在参数配置页新增 category=采样参数 的条目）"。
- **未连接**：两区显示空态"串口未连接"。
- **实时刷新**：每 1s metric 数值重抽 + 趋势曲线追加新点（旧点左移）。切离本页时停止定时器。

---

## 4. 状态策略 statusPolicy

### 4.1 布局图

```text
content (padding 12px)
┌───────────────────────────┬───────────────────────────┐
│ 卡片A 离线判定策略        │ 卡片B 状态转换预览        │
│ card-head + tag "设备总览"│ card-head + tag.warn "10m"│
│ card-body:                │ card-body:                │
│  form-grid (4 字段)       │  table (thead + 4 行)     │  grid cols-2
│  table (无 thead, 4 行)   │                           │
│  [保存策略][恢复默认]     │                           │
└───────────────────────────┴───────────────────────────┘
```

### 4.2 区块清单

| 区块 | 结构 |
| :--- | :--- |
| 卡片A 离线判定策略 | card + card-head + card-body（form-grid + 说明 table + 2 按钮） |
| 卡片B 状态转换预览 | card + card-head + card-body（table 含 thead 4 行转换规则） |

### 4.3 控件清单

- 卡片A form-grid（2 列）：启用离线判定 checkbox（默认勾选）+ 无通讯超时时间 input（number，value 10）+ 时间单位 select（分钟/秒）+ 作用范围 select（全部设备/仅采样设备/自定义设备）。
- 卡片A 说明 table（无 thead，两列）：判定依据 / 在线转离线 / 告警转离线 / 离线恢复，各一行规则文本。
- 卡片A 按钮：保存状态策略（主）+ 恢复默认策略（次）。
- 卡片B table（thead：当前状态/条件/设备总览显示）：4 行在线/告警 × 10 分钟内外的转换结果。

### 4.4 数据字段（状态转换表）

| 当前状态 | 条件 | 显示 |
| :--- | :--- | :--- |
| 在线 | 10 分钟内收到有效数据 | 在线（绿） |
| 在线 | 超过 10 分钟未收到 | 离线（默认色） |
| 告警（橙） | 10 分钟内收到 | 告警（橙） |
| 告警（橙） | 超过 10 分钟未收到 | 离线 |

### 4.5 状态变体

- 超时时间 input 改变时，预览表的"10 分钟"文案应联动（第二阶段补）。
- 启用/禁用离线判定 checkbox 切换时，策略是否生效（第二阶段补）。

---

## 5. 参数配置 params

### 5.1 布局图

```text
content (padding 12px)
┌────────────────────────────────────────────────────────┐
│ 卡片A Modbus RTU 参数定义 (grid 单列，垂直堆叠)        │
│ card-head "…" + tag.warn "未保存"                      │
│ card-body:                                             │
│  [新增][编辑勾选▾][删除勾选▴][导入模板][导出模板]      │
│  param-table (11 列, 首列 checkbox)                    │
├────────────────────────────────────────────────────────┤
│ 卡片B 新增/修改参数                                    │
│ card-head + tag "表单"                                 │
│ card-body:                                             │
│  form-grid (10 字段 + 跨列说明)                        │
│  [保存定义][校验定义][取消修改]                        │
└────────────────────────────────────────────────────────┘
```

### 5.2 区块清单

| 区块 | 结构 |
| :--- | :--- |
| 卡片A 参数定义 | card（tag.warn "未保存"）+ card-body（按钮行 + param-table） |
| 卡片B 表单 | card + card-body（form-grid + 按钮行） |

### 5.3 控件清单

- 卡片A 工具行：新增参数（主）+ 编辑勾选 `data-param-action="edit"`（次，disabled）+ 删除勾选 `data-param-action="delete"`（danger，disabled）+ 导入模板（次）+ 导出模板（次）+ 弹性占位 + "分类筛选"label + **分类筛选自定义下拉**（`.select-custom[data-dropdown-name="paramFilter"]`，选项：全部 / 采样参数 / 配置参数，默认全部）。
  - 筛选下拉控制表格只显示对应 category 的行；"全部"显示所有。筛选状态下编辑/删除只作用于可见行（被筛选掉的行不参与勾选计数）。无匹配行时表格显示空态。
- 卡片A param-table（11 列）：select-cell（`data-param-check-all` 全选）+ 参数名 / 显示名 / 地址 / 分类 / 类型 / 权限 / 单位 / 小数 / 范围 / 说明。每行首列 `data-param-check`。
- 卡片B form-grid：参数名 / 显示名 / Modbus 地址 / 参数分类 select / 数据类型 select / 访问权限 select / 单位 / 小数位数 / 最小值 / 最大值 + 跨列说明 input。
- 卡片B 按钮：保存定义（主）+ 校验定义（次）+ 取消修改（次）。

### 5.4 数据字段（参数表预置 4 行）

| 参数名 | 显示名 | 地址 | 分类 | 类型 | 权限 | 单位 | 小数 | 范围 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| temperature | 温度 | 0x0000 | 采样参数 | uint16 | 只读 | ℃ | 1 | -40~125 | 缩放 0.1 |
| pressure | 压力 | 0x0001 | 采样参数 | uint16 | 只读 | MPa | 2 | 0~60 | 缩放 0.01 |
| sample_period | 采样周期 | 0x0010 | 配置参数 | uint16 | 读写 | ms | 0 | 200~5000 | 写入需确认 |
| device_addr | 设备地址 | 0x0011 | 配置参数 | uint8 | 读写 | - | 0 | 1~247 | 从站地址 |

### 5.5 状态变体（详见交互规范勾选状态机）

- 编辑按钮：仅勾选 1 条时 enabled。
- 删除按钮：勾选 ≥1 条时 enabled。
- 全选 checkbox：三态（全选/部分/未选）。
- **未保存 tag.warn**：参数有变更时显示，第二阶段补"保存后清除"。

---

## 6. 报警记录 alarms

### 6.1 布局图

```text
content (padding 12px)
┌────────────────────────────────────────────────────────┐
│ 卡片 报警记录                                          │
│ card-head "报警记录" + tag.warn "1 未确认"             │
│ card-body:                                             │
│  [确认勾选▾][确认全部未确认][导出报警]                 │
│  alarm-table (7 列, 首列 checkbox)                     │
└────────────────────────────────────────────────────────┘
```

### 6.2 区块清单

| 区块 | 结构 |
| :--- | :--- |
| 卡片 报警记录 | card（tag.warn "1 未确认"）+ card-body（按钮行 + alarm-table） |

### 6.3 控件清单

- 按钮行：确认勾选 `data-alarm-action="ack"`（主，disabled）+ 确认全部未确认 `data-alarm-action="ack-all"`（次）+ 导出报警（次）。
- alarm-table（7 列）：select-cell（`data-alarm-check-all` 全选）+ 时间 / 内容 / 终端 / 级别 / 状态（`data-alarm-status`）/ 确认信息（`data-alarm-ack`）。每行首列 `data-alarm-check`。

### 6.4 数据字段（预置 3 行）

| 时间 | 内容 | 终端 | 级别 | 状态 | 确认信息 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 18:27:58 | 压力接近上限 | 压力采集器 | 预警 | **未确认**（橙） | - |
| 18:18:22 | CRC 异常帧已丢弃 | COM3 | 一般 | 已确认 | 工程师 18:19:04 |
| 17:52:09 | 备用终端离线超过 10 分钟 | 备用终端 | 提示 | 已确认 | 工程师 17:55:21 |

> 未确认行 checkbox 可选；已确认行 checkbox `disabled`，状态文字回退默认色。

### 6.5 状态变体（详见交互规范报警确认状态机）

- 确认前：状态"未确认"（橙），checkbox enabled。
- 确认后：状态"已确认"（默认色），checkbox disabled，确认信息列写入"工程师 HH:MM:SS"，不可逆。
- tag.warn 计数随未确认数量变化（第二阶段补）。

---

## 7. 历史数据 history

### 7.1 布局图

```text
content (padding 12px)
┌───────────────────────────┬───────────────────────────┐
│ 卡片A 查询条件            │ 卡片B 趋势曲线            │
│ card-head + tag "CSV"     │ card-head + tag "统计"    │
│ card-body:                │ card-body:                │
│  form-grid (4 字段)       │  chart (180px)            │  grid cols-2
│  [查询][导出]             │                           │
└───────────────────────────┴───────────────────────────┘
```

### 7.2 区块清单

| 区块 | 结构 |
| :--- | :--- |
| 卡片A 查询条件 | card + card-body（form-grid + 按钮行） |
| 卡片B 趋势曲线 | card + card-body（chart） |

### 7.3 控件清单

- form-grid：开始时间（"2026-06-10 00:00"）/ 结束时间（"2026-06-10 23:59"）/ **点位（多选下拉，选项来自 `store.params` 的采样参数 display 名，默认全选）** / 导出格式（"CSV"）。
  - 点位下拉是 `.select-custom.multi[data-dropdown-name="historyPoints"]`：多选模式，点击选项切换勾选不关闭弹层，触发器显示已选汇总（如"温度、压力"），全不选时显示"请选择"。无采样参数时该字段为禁用输入框"暂无采样参数"。
- 按钮：查询（主）+ 导出（次）。
- 1× `.chart`（180px）：第二阶段换 Chart.js。

### 7.4 数据字段

查询条件 4 项 + 趋势曲线（按点位多曲线）。MVP 优先 CSV，Excel 后续增强。

### 7.5 状态变体

- **无数据态（第二阶段补）**：查询无结果时 chart 区显示"无符合条件的数据"。
- **加载态（第二阶段补）**：查询/导出时按钮 loading。
- 时间范围校验：开始 < 结束（第二阶段补）。

---

## 8. 系统设置 settings

### 8.1 布局图

```text
content (padding 12px)
┌───────────────────────────┬───────────────────────────┐
│ 卡片A 软件信息            │ 卡片B 维护操作            │
│ card-head + tag.ok "正常" │ card-head + tag "诊断"    │
│ card-body:                │ card-body:                │
│  table (无 thead, 4 行)   │  table (无 thead, 4 行)   │  grid cols-2
│                           │  [清理日志][导出诊断]     │
└───────────────────────────┴───────────────────────────┘
```

### 8.2 区块清单

| 区块 | 结构 |
| :--- | :--- |
| 卡片A 软件信息 | card（tag.ok "正常"）+ card-body（键值 table） |
| 卡片B 维护操作 | card（tag "诊断"）+ card-body（键值 table + 按钮行） |

### 8.3 控件清单

- 卡片A table（无 thead，两列键值）：软件名称 multi-protocol-hmi / 应用版本 v0.1.0 / 运行平台 Windows 10/11 / 运行时长 12:36:18。
- 卡片B table（无 thead，两列键值）：数据保存路径 ./save / 日志空间 128/512 MB / 配置文件 config.example.json / 帧错误计数 1。
- 卡片B 按钮：清理日志（次）+ 导出诊断（主）。

### 8.4 数据字段

均为只读展示字段。运行时长应为动态计算（第二阶段补）。

### 8.5 状态变体

- 清理日志：弹确认框（第二阶段补保留时间范围）。
- 导出诊断：打包运行日志/配置/统计（第二阶段补 loading + 成功提示）。

---

## 9. 模型配置 modelConfig

### 9.1 布局图

```text
content (padding 12px)
┌───────────────────────────┬───────────────────────────┐
│ 卡片A 模型提供商          │ 卡片B 编辑提供商          │
│ card-head + tag "N 启用"  │ card-head + tag "表单"    │
│ card-body:                │ card-body:                │
│  [新增][删除勾选]         │  form-grid (字段)         │  grid cols-2
│  provider-table (5 列)    │  [保存][测试连接][取消]   │
│                           │  警告提示条               │
└───────────────────────────┴───────────────────────────┘
```

### 9.2 区块清单

| 区块 | 结构 |
| :--- | :--- |
| 卡片A 模型提供商 | card + card-body（按钮行 + provider-table） |
| 卡片B 编辑提供商 | card（tag "表单"）+ card-body（form-grid + 按钮行 + 警告提示条） |

### 9.3 控件清单

- 卡片A 按钮行：新增提供商 `data-mc-toolbar="create"`（主）+ 删除勾选 `data-mc-toolbar="delete"`（danger，disabled）。
- 卡片A provider-table（6 列）：select-cell（全选 `data-mc-check-all`）+ 提供商 / base_url / 模型 / API Key（脱敏显示 ••••后4位）/ 启用（✓/—，只读展示）。每行首列 `data-mc-check`。
- 卡片B form-grid：**提供商 select `data-mc-field="provider"`（预置 OpenAI / 通义 / DeepSeek / 智谱 / Kimi，选预设自动填 baseUrl + model）** / base_url input / API Key input（`type=password`，`data-mc-field="apiKey"`）/ 模型名 input / 启用 checkbox（跨列，`data-mc-field="enabled"`）。
  - 选预设提供商时（`_onProviderChange`），自动回填对应 base_url 与推荐 model，用户可再改。
- 卡片B 按钮行：保存 `data-mc-form="save"`（主）+ 测试连接 `data-mc-form="test"`（次）+ 取消 `data-mc-form="cancel"`（次）。
- 卡片B 警告提示条：常驻提示"原型阶段不真联网调用 LLM（CORS 限制），PySide6 阶段启用"。校验错误（base_url 非 http / key 空 / 模型空）在字段下方显示 `.field-error` 红字。

### 9.4 数据字段（预置 1 行示例）

| 提供商 | base_url | 模型 | API Key | 启用 |
| :--- | :--- | :--- | :--- | :--- |
| OpenAI | <https://api.openai.com/v1> | gpt-4o-mini | ●●●●●●●●（password） | ✓ |

> 预设映射（选预设自动填）：OpenAI→`https://api.openai.com/v1`+`gpt-4o-mini`；通义→`https://dashscope.aliyuncs.com/compatible-mode/v1`+`qwen-plus`；DeepSeek→`https://api.deepseek.com/v1`+`deepseek-chat`；智谱→`https://open.bigmodel.cn/api/paas/v4`+`glm-4-flash`；Kimi→`https://api.moonshot.cn/v1`+`moonshot-v1-8k`。

### 9.5 状态变体

- 新增/删除按钮启用规则同 params（删除勾选 ≥1 条时 enabled）。
- **校验失败**：base_url 须以 `http://` 或 `https://` 开头；API Key 必填。不通过时字段下方红字 + 不保存。
- **测试连接（模拟）**：点"测试连接"→ 按钮 loading → 延时后 toast"连接成功（模拟）"或"连接失败：{原因}"。
- **持久化**：保存后写入 localStorage key `multi-protocol-hmi-model-config`，下次进入回填。
- **工具栏联动**：保存后工具栏 AI 状态指示更新（已配置→`.stat-ok`；未配置→`.stat-warn`）。

---

## 10. 跨页面通用规则

1. **content 滚动**：所有页 content 区 `overflow:auto`，内容超出时纵向滚动；横向一般不滚（grid 自适应）。
2. **卡片间距**：同层 grid 内卡片 gap 10px；垂直堆叠卡片用 `margin-top:10px`（如 overview 卡片C、params 卡片B）。
3. **grid 列数**：`cols-2`（2 等宽）/ `cols-3`（3 等宽）/ 单列（垂直堆叠）。响应式 ≤1050px 时 cols-2 不变、modal-body 变单列。
4. **tag 位置**：统一在 card-head 右侧或 tree-item 右侧，靠 flex 两端对齐。
5. **按钮组**：内联 `display:flex; gap:8px; margin-top:12px` 或 `margin-bottom:10px`，主按钮在前、次级/danger 在后。

---

## 11. AI 助手页 aiAssistant（标准页面）

> AI 助手是**渲染进 `#content` 的标准页面**（不再是浮动侧栏），走与 monitor/params 等一致的标准路由。页面定义已加入 `mock.pages`，侧边栏「AI 助手」入口用 `data-page="aiAssistant"`。对话气泡/工具卡片/思考动画沿用之前样式。详见交互规范 §9。

```text
content (padding 12px)
┌────────────────────────────────────────────────────────┐
│ 单张大 card（占满 content 区）                          │
│ card-head "✦AI 运维助手" + 模型配置状态 tag             │
│ card-body .ai-page-body (三行 grid，height: calc(100vh - 180px))│
│ ┌──────────────────────────────────────────────────────┐│
│ │ ai-messages  minmax(0,1fr) 可滚  对话历史              ││
│ │   ├─ 用户气泡      右对齐，主色底，白字                 ││
│ │   ├─ 助手气泡      左对齐，白底，边框                   ││
│ │   ├─ 工具调用卡片   函数名 + 参数 + 三态标记            ││
│ │   └─ 思考动画       三点跳动（等待 LLM 响应时）         ││
│ ├──────────────────────────────────────────────────────┤│
│ │ ai-input-wrap 输入区   textarea + 发送按钮(data-ai-send)││
│ ├──────────────────────────────────────────────────────┤│
│ │ ai-hint 提示行   "Ctrl/Cmd+Enter 发送" 等              ││
│ └──────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────┘
```

### 11.1 区块清单

| 区块 | 结构 | 说明 |
| :--- | :--- | :--- |
| card-head | 标准卡片头，标题"✦AI 运维助手" + 模型配置状态 tag（已配置→`.stat-ok`；未配置→`.stat-warn`） | 复用 §6 标准 card-head，不单独需要 .ai-head |
| ai-messages | `.ai-page-body` grid 第一行 `minmax(0,1fr)`，纵向可滚，padding 10px，flex 列方向 | 承载全部对话历史（来自 `store.aiMessages`），含气泡/工具卡/思考动画 |
| ai-input-wrap | `.ai-page-body` grid 第二行，textarea + 发送按钮 | 发送按钮带 `data-ai-send` 属性（豁免 app.js 兜底 click 绑定） |
| ai-hint | `.ai-page-body` grid 第三行，提示文本 | "Ctrl/Cmd+Enter 发送" 等 |

### 11.2 控件清单

- `.ai-bubble-user`：右对齐气泡，主色底 `--primary` + 白字，圆角 6px（右下角小），max-width 80%。
- `.ai-bubble-assistant`：左对齐气泡，白底 + 1px `--line` 边框，圆角 6px（左下角小），max-width 80%。
- `.ai-tool-card`：工具调用卡片，含函数名（800）+ 参数（等宽 muted）+ 状态标记（⏳ running / ✓ done / ✗ error）+ 结果摘要。
- `.ai-thinking`：思考动画，三个圆点依次跳动，等待 LLM/工具响应时显示。
- `.ai-input`：textarea，placeholder"输入问题，Ctrl/Cmd+Enter 发送"。
- `data-ai-send`：发送按钮（主），带 `data-ai-send` 属性豁免 app.js 兜底绑定；空输入时 disabled。

### 11.3 数据字段

| 元素 | 内容 |
| :--- | :--- |
| 欢迎语 | 首条助手气泡："你好，我是 AI 助手，可以查询实时点位、告警、趋势和设备状态。" |
| 用户气泡 | 用户输入文本 |
| 助手气泡 | LLM 生成的自然语言回复 |
| 工具卡 | 函数名 / 参数 / 状态 / 结果摘要 |
| 对话历史 | 存 `store.aiMessages`，切页再回来恢复全部历史气泡 |

### 11.4 状态变体

- **思考中**：ai-messages 末尾显示三点动画，发送按钮 disabled。
- **工具执行中**：对应工具卡标记 ⏳ running；完成→✓ done；失败→✗ error（卡片边框转 `--warn`）。
- **AI 未配置**：未保存任何模型配置时，输入框禁用 + 提示条"未配置模型，请先到模型配置页添加"，工具栏 AI 状态指示 `.stat-warn`。

---

## 12. 版本与维护

- 规范来源：原型 `overviewHtml`/`serialHtml`/`monitorHtml`/`statusPolicyHtml`/`paramsHtml`/`alarmsHtml`/`historyHtml`/`settingsHtml`/`modelConfigHtml` 九个生成函数 + AI 助手页（`mock.pages.aiAssistant`）。
- 第二阶段原型补空/异常态后，每页的"状态变体"段需同步扩充。
- 新增页面时，按本文件五段结构补充。
