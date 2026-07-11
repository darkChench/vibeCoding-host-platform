<!-- markdownlint-disable MD013 MD033 -->
# 上位机交互原型（assets/hmi）

> 这是 `multi-protocol-hmi` 上位机的**交互原型**，作为 PySide6 重写的视觉与交互蓝本。
> 规范文档见 `docs/hmi/`（[总则](../../docs/hmi/ui-restoration-spec.md) / [控件](../../docs/hmi/widget-qss-spec.md) / [页面](../../docs/hmi/page-layout-spec.md) / [交互](../../docs/hmi/interaction-spec.md)）。

## 如何运行

直接用浏览器打开 `index.html` 即可（无需构建、无需服务器）：

- 双击 `index.html`，或拖入浏览器。
- 实时图表（monitor/history）依赖 Chart.js，**首次打开需联网**从 CDN 加载；离线时图表区会显示提示，其余功能不受影响。

## 模块结构

```text
assets/hmi/
├── index.html                          # 入口（结构骨架 + 资源引入）
├── README.md                           # 本文件
├── css/
│   ├── tokens.css                      # 设计令牌（:root 变量）
│   ├── layout.css                      # 窗口网格与工作区骨架
│   ├── widgets.css                     # 原子控件
│   └── pages.css                       # 页面特定样式（预留）
└── js/
    ├── util.js                         # 工具函数（转义、HEX 解析、CRC 等）
    ├── store.js                        # 全局可变状态
    ├── app.js                          # 主入口、路由、全局事件
    ├── data/
    │   └── mock.js                     # 模拟数据集中管理
    ├── components/
    │   ├── toast.js                    # 操作反馈
    │   ├── modal.js                    # 通用动作模态
    │   ├── menu.js                     # 菜单栏弹窗
    │   ├── chart.js                    # Chart.js 封装
    │   ├── dropdown.js                 # 自定义下拉（强制上拉，替代原生 select）
    │   ├── console.js                  # 串口控制台（核心）
    │   ├── modbusProtocol.js           # Modbus RTU 协议层（报文生成+CRC+模拟回包+解析）
    │   ├── aiTools.js                  # AI 工具函数层（只读：点位/告警/趋势/设备状态）
    │   └── llmClient.js                # LLM 调用层（原型模拟 send/summarize）
    └── pages/
        ├── overview.js                 # 首页/总览
        ├── serial.js                   # 设备连接（→ console 组件）
        ├── monitor.js                  # 实时监控
        ├── statusPolicy.js             # 状态策略
        ├── params.js                   # 参数配置（CRUD + 校验）
        ├── alarms.js                   # 报警记录（确认状态机）
        ├── history.js                  # 历史数据
        ├── settings.js                 # 系统设置
        ├── modelConfig.js              # 模型配置（AI 提供商 CRUD + 测试连接）
        └── aiAssistant.js              # AI 助手页（对话 + 工具调用）
```

## 架构说明

- **全局命名空间**：所有模块挂到 `window.HMI.*`，不使用 ES Module——这样原型可以直接 `file://` 打开，无 CORS 限制。
- **加载顺序**：`util → mock → store → components → pages → app`。`app.js` 最后加载并在 `DOMContentLoaded` 时调用 `HMI.app.init()`。
- **页面注册**：每个页面文件向 `HMI.pages.<id> = {render, bind}` 注册，由 `app.js` 统一路由分发。
- **状态集中**：`HMI.store` 管理所有运行时可变状态（当前页、连接状态、发送历史、参数/报警模型等），DOM 只是状态的视图。

## 已实现的交互（相对早期单文件原型的增强）

早期单文件原型（`page-interaction-review-prototype.html`）只做了正常态展示，许多按钮是占位。本版本补全了：

| 区域 | 增强内容 |
| :--- | :--- |
| serial 串口台 | HEX/ASCII 切换解析、行结束符追加、自动发送定时（min 100ms）、发送历史完整 CRUD、未连接态提示 |
| params 参数配置 | 真实 CRUD（新增/编辑载入/删除移除）、字段校验（名称/地址/范围/小数位）、未保存标记、全选三态 |
| alarms 报警记录 | 基于模型的确认状态机、未确认计数联动 tag |
| monitor/history | Chart.js 真实图表（坐标轴/tooltip/多曲线），monitor 实时刷新，history 查询 loading + 空态 |
| settings | 清理日志二次确认、导出诊断 loading |
| AI 助手 | 独立页面（标准路由，对话历史切页保留）、对话流程（思考动画→工具调用卡片→结果摘要→自然语言回复）、4 个只读工具（read_sensor/get_alarms/get_trend/get_device_status）、Ctrl/Cmd+Enter 发送 |
| modelConfig 模型配置 | 预设提供商自动填 baseUrl+model、表单校验（http 开头/key 必填）、测试连接（模拟）、CRUD、localStorage 持久化、工具栏 AI 状态指示联动 |
| 全局 | 未连接/无数据/loading/校验失败 等空/异常态 |

## 验证

原型已通过自动化验证（非仅浏览器肉眼检查）：

- **JS 语法**：17 个 JS 文件 `node --check` 全过。
- **核心逻辑单测**：util 13 项（HEX 解析/CRC/转义）、store 11 项（发送历史去重置顶/截断/查找）。
- **DOM 集成测试（jsdom）**：完整加载 index.html + 18 个 JS、执行 `init()`，验证 8 页面渲染、params CRUD、alarms 确认状态机、console 发送、连接状态机联动、PRD 编辑器——共 39 项全部通过。
- **HTTP 冒烟**：23 个资源全部 200 OK。

> 浏览器肉眼验收仍建议执行：双击 `index.html`，重点看 Chart.js 图表渲染（jsdom 无法验证 Canvas，需真实浏览器 + 联网加载 CDN）。

## 与 PySide6 重写的关系

本原型是**视觉与交互的真相源**，但**不是最终实现**：

- 颜色、尺寸、字号、网格 → 以 `docs/hmi/ui-restoration-spec.md` 令牌为准。
- 控件映射 → 以 `docs/hmi/widget-qss-spec.md` 为准。
- 页面结构 → 以 `docs/hmi/page-layout-spec.md` 为准。
- 行为细节 → 以 `docs/hmi/interaction-spec.md` 为准。

PySide6 重写时，本原型的 JS 逻辑**不复用**（语言不同），但可作为行为参考——尤其状态机与异常态处理。
