# 文档中心

本目录是 vibeCoding-host-platform 项目的文档知识库，为开发者和 AI Agent 提供完整的项目文档。

---

## 目录结构

```
docs/
├── README.md              # 本文件
├── AGENTS.md              # docs 目录的 AI Agent 操作手册
├── agents/                # Agent 工作流文档
│   ├── domain.md           # 单上下文域文档（CONTEXT.md + ADR）
│   ├── issue-tracker.md    # 本地 markdown issue 跟踪器规范
│   └── triage-labels.md    # 5 个默认 triage 标签
├── hmi/                   # HMI 上位机设计与规范
│   ├── product-requirements.md    # 产品需求文档（PRD）
│   ├── page-layout-spec.md        # 页面布局规范（ASCII 布局图）
│   ├── interaction-spec.md        # 交互规范（导航/状态机/协议层）
│   ├── ui-restoration-spec.md     # 界面还原规范（设计 token）
│   ├── widget-qss-spec.md         # 控件 QSS 映射规范
│   └── component-style-reference.md # 组件样式参考手册
├── references/            # 参考资料
│   ├── project-architecture-template.md  # 项目架构模板
│   ├── quality-gates-and-pitfalls.md     # 质量门禁与常见坑
│   └── quality-gates-and-pitfalls-hmi.md # HMI 专项质量门禁
└── workFlow/              # 开发工作流
    ├── README.md            # 工作流说明
    ├── AGENTS.md            # 工作流 Agent 手册
    └── development-process.md # 开发流程
```

---

## 快速导航

### 新人入门
1. [产品需求文档](hmi/product-requirements.md) — 了解产品要做什么
2. [页面布局规范](hmi/page-layout-spec.md) — 每个页面的 ASCII 布局图
3. [交互规范](hmi/interaction-spec.md) — 导航、状态机、协议层设计

### UI 还原
1. [界面还原规范](hmi/ui-restoration-spec.md) — 设计 token（颜色/字号/圆角）
2. [控件 QSS 映射](hmi/widget-qss-spec.md) — HTML 控件 → PySide6 → QSS
3. [组件样式参考](hmi/component-style-reference.md) — 每个组件的最终渲染样式值

### 开发流程
1. [开发流程](workFlow/development-process.md) — 从原型到 PySide6 的迁移流程
2. [Issue 跟踪器](agents/issue-tracker.md) — 本地 markdown issue 管理
3. [质量门禁](references/quality-gates-and-pitfalls.md) — 常见坑与修复

---

## 技术栈

| 层 | 技术 |
|:---|:---|
| UI 框架 | PySide6 6.11 (Qt6) |
| 语言 | Python 3.11 |
| 串口通信 | pyserial 3.5 |
| 协议 | Modbus RTU（功能码 03/06） |
| 图表 | QtCharts |
| 数据库 | SQLite（历史数据） |
| AI | OpenAI 兼容 / Anthropic 兼容 LLM API |
