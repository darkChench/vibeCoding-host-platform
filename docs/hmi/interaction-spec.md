<!-- markdownlint-disable MD013 MD033 -->
# 交互规范 · 导航 / 状态机 / 异常态

> 用途：固化原型所有交互行为与状态机，并标注哪些是原型已实现、哪些是第二阶段待补全。让 PySide6 重写时行为零歧义。
>
> 配套：布局见 [页面布局规范](page-layout-spec.md)，控件样式见 [控件映射规范](widget-qss-spec.md)。

---

> ℹ️ **实现状态更新（第二阶段原型扩展完成后）**
>
> 原型已从单文件拆分为模块化工程（`assets/hmi/index.html` 为新入口），本文档中所有 🆕 **待补全**项均已落地实现，对应代码位置：
>
> - serial 串口台（HEX/ASCII 切换、行结束符、自动发送、发送历史 CRUD、未连接态）→ `js/components/console.js`
> - params 真实 CRUD + 字段校验 + 未保存标记 + 全选三态 → `js/pages/params.js`
> - alarms 基于模型的确认状态机 + 未确认计数联动 → `js/pages/alarms.js`
> - 空/异常态（未连接、无数据、loading、校验失败）→ 各页面 `render()` 内分态渲染 + `widgets.css` 的 `.empty-state/.btn.loading/.console-notice/.field-error`
> - 菜单"清空串口日志/导出 CSV"等仍为占位（走通用动作弹窗），待接入真实文件 IO
>
> 下文保留 ✅/🆕 原标注以记录"原型初版 vs 扩展版"的差异演进，PySide6 重写时以**扩展版行为**为准。

## 标注约定

- ✅ **已实现**：原型初版即有的行为。
- 🆕 **待补全**：原型初版占位、第二阶段已补全的行为（实现位置见上方横幅）。
- 标注在每个条目末尾。

---

## 1. 导航交互

### 1.1 页面切换核心 showPage(pageId)

切换页面时按顺序执行（PySide6 应等价建模）：

1. 更新 `currentPageId`。
2. 更新标题栏副文字 `Windows 上位机 - {page名}`。
3. 更新状态栏右侧 `{page名}`。
4. 切换侧边栏 tree-item 的 active 态（`data-page === pageId`）。
5. 重渲 tabs 行（active 态随 currentPageId）。
6. 重渲 content 主区（调用对应 xxxHtml）。✅

### 1.2 四种导航入口

| 入口 | 触发 | 行为 | 状态 |
| :--- | :--- | :--- | :--- |
| 侧边栏 tree-item | click `[data-page]` | `showPage(dataset.page)` | ✅ |
| 顶部 tabs | click `.tab[data-page]` | `showPage(dataset.page)` | ✅ |
| 首页 quick-card | click `[data-jump]` | `showPage(dataset.jump)` | ✅ |
| 菜单弹窗项 | click 菜单项 | 命中 `pageByLabel` 则跳转，否则走动作弹窗 | ✅ |

`pageByLabel` 文案映射（菜单/按钮文案 → pageId）：

```text
"设备总览"/"首页/总览" → overview
"串口连接" → serial
"实时监控" → monitor
"状态策略" → statusPolicy
"参数配置" → params
"报警记录" → alarms
"历史数据" → history
"系统设置" → settings
```

### 1.3 菜单栏弹窗

- 点击 `.menu-item` → `event.stopPropagation()` + 打开 `#menuPopup`，定位 `left=按钮左, top=按钮底+2px`。✅
- `menuActions` 字典（6 个菜单各自的子项）：

```text
文件: [新建项目, 打开配置, 保存配置, 导入参数模型, 导出参数模型, 退出]
连接: [连接串口, 断开串口, 刷新串口, 清空串口日志]
设备: [设备总览, 串口连接, 实时监控, 状态策略, 参数配置]
数据: [报警记录, 历史数据, 导出 CSV, 清空历史缓存]
工具: [PRD 表格, 诊断包, 日志清理, 系统设置]
帮助: [关于软件, 快捷键, 使用文档]
```

- 点击菜单项 → 关闭弹窗 + `handleMenuAction`：
  - "PRD 表格" → 打开 PRD 模态。✅
  - "连接串口"/"断开串口" → `setConnectionState(true/false)`。✅
  - "刷新串口" → toast"串口列表已刷新"。✅
  - 其余 → `handlePrototypeAction`（走 pageByLabel 跳转或 actionDetails 弹窗或兜底文案）。✅
- 点 document 空白处 → 关闭弹窗。✅
- 🆕 "清空串口日志"/"导出 CSV"/"清空历史缓存"/"诊断包"/"日志清理"/"关于软件"等无定义项，第二阶段补真实行为或明确"待实现"提示。

### 1.4 普通表格行选中

- 非 param-table、非 alarm-table 的 `.table tbody tr` click → 清除同 tbody 其他行 `.selected` + 当前行加 `.selected` + toast"已选中：{首格文本}"。✅

---

## 2. 串口台（serial 页）

### 2.1 console 3-tab 切换

- click `.console-tab[data-console]` → 移除所有 console-tab 的 active + 当前列加 active → 替换 `.terminal` 内容为对应数据（raw/stats/diagnostic）。✅
- 🆕 切换时保留滚动位置与时间戳筛选（第二阶段补）。

### 2.2 发送历史 popover

localStorage key `multi-protocol-hmi-send-history`，最多 20 条，去重置顶。

| 操作 | 触发 | 行为 | 状态 |
| :--- | :--- | :--- | :--- |
| 打开/关闭 | click `[data-send-history-toggle]` | 先 `renderSendHistory()` 再 toggle `.open` | ✅ |
| 选择 | click `.history-pick` | 把帧写入 `.send-input.value` + focus + 关闭 popover | ✅ |
| 删除单条 | click `.history-delete` | 从 sendHistory 过滤该项 + 持久化 + 重渲 + toast"已删除发送历史" | ✅ |
| 清空全部 | click `[data-send-history-clear]` | sendHistory=[] + 持久化 + 重渲 + toast"发送历史已清空" | ✅ |
| 空态 | 列表为空 | 显示 `.history-empty`"暂无发送历史" | ✅ |
| 持久化失败 | localStorage 写入异常 | toast"发送历史未能写入本地存储" | ✅ |

`saveSendHistory(value)` 规则：归一化（压缩空白）→ 去重 → 置顶 → 截断 20 → 持久化 → 重渲。✅

默认历史 4 条（localStorage 空时回退）：

```text
01 03 00 00 00 04
01 06 00 10 00 01
01 03 00 04 00 02
01 10 00 20 00 02 04 00 64 00 C8
```

### 2.3 发送动作

- click `[data-send-action]` → `handleSendFrame`：取 `.send-input.value` 归一化，空则 toast"发送帧不能为空"；否则 `saveSendHistory(frame)` + toast"已保存到最近发送" + `showAction("发送", ...)` 弹通用动作框。✅
- 🆕 **真实发送逻辑（第二阶段补）**：
  - HEX 模式：按空格拆分转字节；ASCII 模式：直接编码。
  - 行结束符：无/CR(\r)/LF(\n)/CRLF(\r\n) 追加到帧尾。
  - 自动发送 checkbox 勾选时，按间隔（ms，min 100，step 100）定时发送；取消勾选停止。
  - 间隔校验：< 100 时夹紧到 100 并提示。

### 2.4 连接状态切换

- toolbar "连接"按钮 click → 按当前文本决定：`setConnectionState(文本 === "连接")`。✅
- `setConnectionState(connected)`：
  - 改 `.stats-strip` 首 span 文本（"COM3 已连接"/"COM3 未连接"）+ toggle `.stat-ok`。✅
  - 改按钮文本（"断开"/"连接"）。✅
  - toast"串口已连接"/"串口已断开"。✅
- 菜单"连接串口"/"断开串口"联动同一函数。✅
- 🆕 **未连接态（第二阶段补）**：terminal 顶部提示"串口未连接"，发送按钮 disabled 或点击提示先连接。

---

## 3. 参数配置（params）勾选状态机

### 3.1 勾选 → 按钮启用规则 updateParamActionState

| 按钮 | 启用条件 | 状态 |
| :--- | :--- | :--- |
| 编辑勾选 `data-param-action="edit"` | **恰好 1 条**勾选 | ✅ |
| 删除勾选 `data-param-action="delete"` | **≥ 1 条**勾选 | ✅ |

- 全选 checkbox `data-param-check-all` 三态：
  - 全部勾选 → checked=true。
  - 部分勾选 → indeterminate=true。
  - 未选 → checked=false。✅

### 3.2 全选联动

- 全选 change → 把所有 `data-param-check` 设为与全选一致 + `updateParamActionState`。✅
- 单个 checkbox change → `updateParamActionState`。✅

### 3.3 编辑/删除动作

- `edit`：若 `!== 1` 条 → toast"编辑参数时只能勾选 1 条"；否则 `showAction("编辑勾选", "载入参数 {name} 到下方表单")`。✅（**仅弹框，未真正载入**）
- `delete`：若 0 条 → toast"请先勾选要删除的参数"；否则 `showAction("删除勾选", "准备删除 N 条：a、b、c")`。✅（**仅弹框，未真正删除**）

### 3.4 🆕 真实 CRUD（第二阶段补全）

| 动作 | 行为 |
| :--- | :--- |
| 新增参数 | 清空表单，进入新增态 |
| 编辑勾选（1 条） | 把选中行数据载入表单各字段 |
| 删除勾选 | 二次确认后从表格移除选中行；tag.warn"未保存"显示 |
| 保存定义 | 校验地址/类型/权限/范围/小数位 → 通过则更新表格（新增追加/编辑替换） |
| 校验定义 | 不保存，仅检查字段完整性与范围合法性 |
| 取消修改 | 放弃表单修改，恢复为表格选中行或清空 |
| 导入/导出模板 | 从本地配置文件导入 / 导出当前模型为 JSON |

校验规则（按 PRD §8.3 与原型 actionDetails）：

- 参数名：非空，唯一。
- Modbus 地址：合法 hex（0x0000-0xFFFF），不重复。
- 数据类型：uint8/uint16/int16/uint32/int32/float32/bool 之一。
- 访问权限：只读/只写/读写。
- 范围：min ≤ max。
- 小数位：≥ 0 整数。

### 3.5 分类筛选（第二阶段新增）

工具栏右侧的分类筛选下拉（自定义 `.select-custom`，三选项：全部 / 采样参数 / 配置参数，默认"全部"）：

- 选择"采样参数"/"配置参数" → 表格只显示对应 `category` 的行；`store.paramFilter` 更新；toast"已筛选：xxx"。
- 选择"全部" → 恢复显示所有参数。
- 筛选状态下，编辑/删除的勾选计数**只作用于可见行**（被筛选掉的行不参与）。
- 筛选后无匹配行 → 表格显示空态"当前筛选下无参数"。
- 筛选状态保存在 `store.paramFilter`，切页再回来仍保留。

> 与实时监控页的联动：实时监控页只读取 `category="采样参数"` 的条目，与本页筛选独立——筛选只影响本页表格视图，不改变 store.params 数据。

---

## 3.6 实时监控曲线显隐（monitor 页，第二阶段新增）

趋势曲线 card-head 右侧的 chip 列表，每个 chip 对应一个采样参数曲线：

- 点击 chip → 切换 `store.curveVisible[paramName]`（默认 true），chip 加/去 `.inactive` 类（淡化 + 删除线），曲线立即重绘。
- 曲线只画"启用集"（`curveVisible[name] !== false` 的采样参数）。
- 全部 chip 隐藏时，图表区显示空态"所有曲线已隐藏，点击上方标签显示"。
- **颜色稳定**：曲线颜色按采样参数在完整列表中的索引固定（不因显隐重排），隐藏中间曲线不影响其他曲线颜色。
- chip 与曲线随 `store.params` 增删自动跟随（在参数页加采样参数，回本页出现新 chip）。

---

## 3.7 历史数据点位多选与查询联动（history 页，第二阶段新增）

点位字段是**多选下拉**（`.select-custom.multi`），选项来自 `store.params` 的采样参数（用 display 名）：

- **多选交互**：点击选项切换勾选（✓ 标记），**不关闭弹层**，触发器实时更新已选汇总（如"温度、压力"），全不选显示"请选择"。
- **默认全选**：首次进入或 `store.historySelectedPoints` 为 null 时，所有采样参数默认选中。
- **状态保留**：选中项存 `store.historySelectedPoints`（name 数组），切页再回来保留。
- **跟随增删**：在参数页加采样参数，回本页下拉选项自动增加。
- **无采样参数**：字段显示为禁用输入框"暂无采样参数"。
- **查询联动**：点"查询"后，趋势曲线按**当前选中的点位**生成（颜色按采样参数在完整列表中的索引固定，与 monitor 页一致）；未选点位时查询拦截并 toast"请至少选择一个点位"。
- **导出联动**：导出 CSV 的提示文案包含选中点位清单；未选点位时拦截。

---

## 4. 报警记录（alarms）确认状态机

### 4.1 勾选 → 按钮启用规则 updateAlarmActionState

| 按钮 | 启用条件 | 状态 |
| :--- | :--- | :--- |
| 确认勾选 `data-alarm-action="ack"` | **≥ 1 条**勾选（仅未确认行可勾） | ✅ |

- `checks` 统计仅 `[data-alarm-check]:not(:disabled)`（**已确认行不参与计数**）。✅
- 全选三态同参数页，但只覆盖未确认行。✅

### 4.2 确认动作 handleAlarmAction

- `ack`：取选中行，空则 toast"请先勾选未确认报警"，否则 `acknowledgeAlarmRows(选中行)`。✅
- `ack-all`：取所有未确认行（`[data-alarm-check]:not(:disabled)`），空则 toast"没有未确认报警"，否则批量确认。✅

### 4.3 确认写状态 acknowledgeAlarmRows（核心，不可逆）

对每行执行：

1. 取当前时间 `HH:MM:SS`。
2. `[data-alarm-status]` 文本 → "已确认" + 清除内联 color（`style.color=""`，回退默认色）。
3. `[data-alarm-ack]` 文本 → "工程师 HH:MM:SS"。
4. `[data-alarm-check]` → `checked=false` + **`disabled=true`（永久禁用，不可再选）**。
5. 调 `updateAlarmActionState` 刷新按钮。
6. `showAction("报警确认", "已确认 N 条报警...")`。✅

> **PySide6 建模建议**：报警模型增加 `acknowledged: bool` + `ack_user: str` + `ack_time: str` 字段。checkbox enabled 绑定 `not acknowledged`；状态委托按 `acknowledged` 决定文字与颜色。确认操作更新模型 → 刷新视图，**不要靠 DOM 不可逆禁用**。

### 4.4 🆕 状态联动（第二阶段补）

- card-head tag.warn "N 未确认"：N 随未确认数量动态变化。
- 确认全部后 tag 消失或变 tag.ok "全部已确认"。

---

## 5. PRD 表格编辑器（模态）

### 5.1 打开

- 工具栏树"PRD 表格"`#openPrdBtn` click 或 菜单"工具 → PRD 表格" → `renderReviewRows()` + 打开 `#prdModal`。✅

### 5.2 编辑（contenteditable）

- 每个单元格 `contenteditable="true"` + `data-key="page|feature|controls|note"`。
- input 事件 → 归一化文本写回 `pages[index][key]` → `markdownOutput.value = buildMarkdown()` 实时重生成 Markdown → **若编辑的页正是当前页，调 `showPage(currentPageId)` 重渲主区**。✅

### 5.3 buildMarkdown

生成标准 Markdown 表格（`| 页面 | 主要功能 | 关键控件 | 备注 |` + 分隔行 + 每页一行），`|` 转义为 `\|`，空白压缩。✅

### 5.4 按钮

| 按钮 | 行为 | 状态 |
| :--- | :--- | :--- |
| 新增页面 `#addRowBtn` | push `{id:"custom-{timestamp}", page:"新页面", 其余:"TODO"}` + 重渲行 + 重渲 tabs | ✅ |
| 恢复初稿 `#resetBtn` | pages = 深拷贝 initialPages + currentPageId="overview" + 重渲 + toast"已恢复初稿" | ✅ |
| 复制 Markdown `#copyBtn` | buildMarkdown 刷新 textarea + select + `navigator.clipboard.writeText`（失败回退 execCommand）+ toast | ✅ |
| 关闭 `#closePrdBtn` / 点 backdrop | 关闭模态 | ✅ |

> **PySide6 注意**：contenteditable → showPage 重渲会丢失焦点，Qt 中若要等价行为需小心信号循环（PRD 编辑触发当前页重渲）。建议 PRD 编辑与主区解耦，编辑时不实时重渲主区，仅保存时同步。

---

## 6. 通用动作模态 actionModal

### 6.1 showAction(title, detail)

设 `#actionTitle` + `#actionBody.innerHTML`（`<strong>{当前页名}</strong>` + `<div>{detail}</div>`，detail 经 escapeHtml）+ 打开 `#actionModal`。✅

### 6.2 按钮

- closeBtn / cancelBtn / 点 backdrop → `closeAction`。✅
- confirmBtn → `closeAction` + toast"操作已确认"。✅

### 6.3 actionDetails 字典（18 个动作键）

prototype 通用按钮（无专用逻辑者）走此字典取说明文本，未命中走兜底"这是原型交互占位，用于评审该按钮是否需要保留、改名或补充真实流程"。

| 动作键 | 说明 |
| :--- | :--- |
| 发送 | 模拟发送当前输入框帧，记录一次 TX |
| 保存定义 | 保存当前参数模型定义（仅维护模型，不读写设备） |
| 校验定义 | 检查参数名/地址/类型/权限/范围等完整性 |
| 取消修改 | 放弃表单修改，恢复表格选中定义 |
| 新增参数 | 清空表单进入新增态 |
| 编辑勾选 | 载入唯一勾选参数到表单 |
| 删除勾选 | 删除勾选参数（需二次确认） |
| 导入模板 | 从本地配置导入参数模型 |
| 导出模板 | 导出当前参数模型为配置文件 |
| 确认勾选 | 确认勾选报警，记录确认人/时间 |
| 确认全部未确认 | 批量确认筛选结果中未确认报警 |
| 导出报警 | 导出报警为 CSV/诊断附件 |
| 查询 | 按时间范围和点位查询历史 |
| 导出 CSV | 导出当前查询结果 |
| 清理日志 | 清理本地诊断日志（需确认保留范围） |
| 导出诊断 | 打包运行日志/配置/通信统计 |
| 保存状态策略 | 保存状态判定规则 |
| 恢复默认策略 | 恢复默认：启用离线判定，10 分钟无通讯离线 |

> 🆕 第二阶段：把"仅弹占位框"的动作升级为真实逻辑（见各页 CRUD 段），或保留为评审占位并明确标注。

---

## 7. 空 / 异常态清单（🆕 第二阶段补全）

原型当前只有"正常态"。下表是需要补全的异常态及其在各页的表现：

| 状态 | 触发条件 | 表现 |
| :--- | :--- | :--- |
| **未连接** | 串口未连接 | serial 页 terminal 顶部提示"串口未连接，请先在工具栏连接"；发送按钮 disabled；连接按钮高亮 |
| **无数据** | monitor 无采样 / history 查询无结果 | metric 显示"--"；chart 区显示空占位"暂无采样数据"/"无符合条件的数据" |
| **加载中** | history 查询/导出、诊断导出进行中 | 触发按钮 loading（文案变"查询中..."/"导出中..."），完成后恢复 |
| **断线** | 通信中断（模拟） | 状态栏显示"通信中断"；设备总览对应设备标红/灰；terminal diagnostic 输出 WARN |
| **超时** | 单次请求超时 | terminal 输出 TIMEOUT 行；stats 累计超时计数 +1 |
| **CRC 错误** | 收到错误帧 | terminal 输出后丢弃；stats CRC 计数 +1；报警表新增"一般"级别记录 |
| **表单校验失败** | params 保存/校验不通过 | 字段下方红字提示具体原因；不关闭表单 |
| **操作确认** | 删除参数/清理日志/高风险操作 | 弹 actionModal 二次确认，确认才执行 |

### 7.1 状态优先级

同一控件/区域可能同时满足多个异常条件，按优先级展示：

```text
未连接 > 断线 > 超时 > CRC 错误 > 无数据 > 正常态
```

### 7.2 PySide6 建模建议

- 用统一的 `ConnectionState` 枚举（Disconnected/Connecting/Connected/Error）驱动 toolbar 按钮文案与 stats-strip。
- 用 `DeviceStatus` 枚举（Online/Alarm/Offline）驱动设备总览与 monitor。
- 异常态文案集中在 `i18n` 或常量模块，不在 UI 代码硬编码。

---

## 8. 全局事件绑定清单（PySide6 信号映射参考）

原型脚本底部（行 2126-2214）的全局绑定，对应 PySide6 信号连接：

| 原型事件 | PySide6 信号 |
| :--- | :--- |
| `.menu-item` click | `QPushButton.clicked` → 打开 QMenu |
| document click 关闭菜单 | QMenu 自带焦点管理（无需手写） |
| `.toolbar .select` change | `QComboBox.currentTextChanged` → toast |
| toolbar 连接按钮 click | `QPushButton.clicked` → setConnectionState |
| 刷新串口按钮 click | `QPushButton.clicked` → toast |
| actionModal 三按钮 | `QDialog` 按钮 `accepted/rejected` |
| `.tree-item[data-page]` click | `QListWidget.currentRowChanged` 或 itemWidget 按钮 `clicked` |
| `#openPrdBtn` click | 按钮 `clicked` → 打开 PRD QDialog |
| addRow/reset/copy | 各按钮 `clicked` |
| `bindDynamicActions` 兜底 | 各页按钮 `clicked` → handlePrototypeAction |

---

## 9. AI 助手对话流程（第二阶段新增）

> AI 助手是**渲染进 `#content` 的标准页面** `aiAssistant`（不再是浮动侧栏组件），走与 monitor/params 等一致的标准路由。布局与控件见 [页面布局规范 §11](page-layout-spec.md)。实现位置：`js/pages/aiAssistant.js` + `js/components/llmClient.js` + `js/components/aiTools.js`。

### 9.1 页面路由（标准页面）

- 侧边栏「AI 助手」`data-page="aiAssistant"` click → `showPage('aiAssistant')`，走标准路由（与 monitor/params 等页面一致）：更新 `currentPageId`、侧边栏 active 态、tabs 行、重渲 content 主区。
- 对话 UI 渲染进 `#content`（不再是浮动 `.ai-aside`），无 toggle/.ai-open 逻辑。
- 发送按钮带 `data-ai-send` 属性，**豁免 `app.js` `_bindGenericActions` 的兜底 click 绑定**（否则会被当 prototype 按钮触发 `showPage` 误覆盖 content）。
- 对话历史存 `store.aiMessages`，切页再回来恢复全部历史气泡。

### 9.2 对话流程（核心链路）

> 对话 UI 渲染进 `#content`（标准页面内），气泡/工具卡/思考动画的追加位置不变，只是容器从浮动 `.ai-aside` 改为页面内的 `.ai-messages`。

```text
用户输入 → ai-messages 追加用户气泡（右/主色）
        → 显示思考动画（三点跳动）
        → llmClient.send(userText)
            ├─ 不需工具 → llmClient 直接生成回复 → 追加助手气泡
            └─ 需调用工具 → 显示工具调用卡片（函数名 + 参数）
                          → aiTools.call(fn, args) 执行
                          → 卡片状态 running→done/error + 显示结果摘要
                          → llmClient.summarize(工具结果, 上下文)
                          → 追加助手气泡（自然语言）
```

- 思考动画与工具卡片按链路实时更新：思考中禁用发送按钮，工具执行中卡片标 ⏳。
- 多轮上下文：`ai-messages` 内全部对话历史作为上下文传给 `llmClient`。

### 9.3 工具调用卡片三态

| 状态 | 标记 | 说明 |
| :--- | :--- | :--- |
| running | ⏳ | 工具正在执行，卡片边框默认色 |
| done | ✓ | 执行成功，下方追加结果摘要 |
| error | ✗ | 执行失败，卡片边框转 `--warn`，显示错误原因 |

### 9.4 快捷键

- **Ctrl/Cmd + Enter**：textarea 内触发发送（等价点发送按钮）。空输入不发送。
- Enter（无修饰键）：换行。

### 9.5 模型配置页交互（modelConfig 页，第二阶段新增）

| 操作 | 行为 |
| :--- | :--- |
| 选预设提供商 | 提供商 select 选 OpenAI/通义/DeepSeek/智谱/Kimi 时，自动回填 base_url 与推荐 model（见页面布局规范 §9.4 映射表），用户可再改 |
| 表单校验 | base_url 须以 `http://` 或 `https://` 开头；API Key 必填；不通过时字段下方红字 + 不保存 |
| 测试连接 | 点"测试连接"→ 按钮 loading → 延时模拟 → toast"连接成功（模拟）"或"连接失败：{原因}"（原型阶段模拟，不真实联网） |
| 新增/删除 | 新增清空表单进入新增态；删除勾选 ≥1 条后 enabled，二次确认后从表格移除 |
| 持久化 | 保存后写入 localStorage key `multi-protocol-hmi-model-config`，下次进入回填 |
| 工具栏联动 | 保存后工具栏 AI 状态指示更新：已配置→`.stat-ok`"AI 就绪"；未配置→`.stat-warn`"AI 未配置" |

---

## 10. AI 工具函数层（第二阶段新增）

> 实现：`js/components/aiTools.js`。供 AI 助手在对话中调用的工具，全部**只读**——读 `HMI.store` 运行时状态，不写设备、不改配置。原型阶段返回值在参数 `min/max` 范围内随机生成。

| 工具函数 | 用途 | 参数 |
| :--- | :--- | :--- |
| `read_sensor(point)` | 读取指定点位的实时值（取 store 对应采样参数当前值） | `point`：点位参数名，如 `temperature` |
| `get_alarms(level, unacknowledged)` | 查询报警列表（按级别/是否未确认筛选） | `level`：级别（预警/一般/提示，可选）；`unacknowledged`：bool，仅未确认（可选） |
| `get_trend(point)` | 取指定点位的短周期趋势数据（monitor 页曲线最近 N 点） | `point`：点位参数名 |
| `get_device_status()` | 取设备总览状态（在线/告警/离线计数与明细） | 无 |

> 全部只读、读 store 运行时状态。工具执行结果由 `llmClient.summarize` 转为自然语言回复。
>
> 第三阶段起，`read_sensor` 和 `get_trend` 的值来源改为走 **Modbus 协议层**（见下节），不再是纯随机数。

---

## 10.1 Modbus 协议层（第三阶段新增）

协议层是**内部逻辑**（报文格式固定，不让用户碰），把参数表的 address/type/access 翻译成真实 Modbus RTU 报文。实现：`js/components/modbusProtocol.js`，挂 `HMI.modbus`。

**核心方法**：

- `readParam(param) → Promise<{ok, value, raw, frame, response}>`：生成读请求帧（功能码 03）→ 注入串口日志 TX → 模拟串口延迟 → 模拟设备回包（真实响应格式）→ 注入串口日志 RX → 按 decimals 解析工程值。
- `writeParam(param, engValue) → Promise<{ok, frame, response}>`：生成写请求帧（功能码 06）→ 注入 TX → 模拟延迟 → echo 回包 → 注入 RX。

**报文格式**（Modbus RTU 标准，CRC16 低字节在前）：

```text
读请求 TX:  [slaveId, 0x03, addrHi, addrLo, qtyHi, qtyLo, crcLo, crcHi]
            例 读温度(0x0000,uint16,slaveId=1): 01 03 00 00 00 01 84 0A
读响应 RX:  [slaveId, 0x03, byteCount, dataHi, dataLo, crcLo, crcHi]
            例 温度25.0℃(raw=250=0x00FA): 01 03 02 00 FA ...
写请求 TX:  [slaveId, 0x06, addrHi, addrLo, valHi, valLo, crcLo, crcHi]
            例 写采样周期(0x0010)=1000ms(0x03E8): 01 06 00 10 03 E8 ...
写响应 RX:  = 请求帧原样返回（echo，Modbus 规范）
```

**关键规则**：

- **type → 寄存器数量**：uint8/int16/uint16/bool → 1 寄存器；uint32/int32/float32 → 2 寄存器。
- **access → 功能码**：读用 03（Read Holding）；写用 06（Write Single）。
- **工程值缩放**：原始值 / 10^decimals = 工程值（如 raw=250, decimals=1 → 25.0）。
- **从站地址**：报文第一字节，来自 `store.slaveId`（默认 1），参数配置页可改（1-247）。
- **自动注入串口日志**：每次 readParam/writeParam 的 TX/RX 都 push 到 `console.lines.raw` 并 appendLine，切到串口页能看到所有自动收发的报文流。
- **模拟回包**：原型阶段设备回包在参数 min/max 范围内随机生成原始值；PySide6 阶段把 `simulateReadResponse` 换成 `pymodbus.client.read_holding_registers`，接口不变。

**调用方**：

- monitor 页 `_startRefresh`：每秒对每个采样参数调 `await HMI.modbus.readParam(p)`，刷新 metric 卡和趋势曲线。
- AI 工具 `read_sensor`/`get_trend`：走 `await HMI.modbus.readParam`，返回契约不变。
- 串口页手动发送（console.handleSend）：**独立路径**，不走协议层，是工程师调试用的 HEX 手动收发。

**注意（数据定义层面）**：type 与 min/max 须匹配——uint16 是无符号，无法表示负数 raw。若点位范围含负数（如温度 -40~125），应定义 type 为 int16，否则协议层返回值会在 0~max 范围。

---

## 11. 版本与维护

- 规范来源：原型 JS（行 1214-2215）。
- 第二阶段原型补全占位交互与异常态后，本文件相应条目的 🆕 标注应转为 ✅ 并补充实现细节。
- 新增交互时，按本文件结构补充，并标注状态。
