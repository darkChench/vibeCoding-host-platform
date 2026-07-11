# vibeCoding-host-platform：上位机Vibe Coding指南

从想法到产品的 AI 结对编程工作流标准：Prompt + Skill + Context + Quality Gate + 工程闭环


### 入口关系

| 入口                             | 你该怎么理解                                           |
| :------------------------------- | :----------------------------------------------------- |
| [docs](docs/README.md)              | 知识库总入口，先从这里选择学习路线                     |
| [workflow]()                        | 项目执行入口，把需求推进成计划、修改、门禁、提交和复盘 |
| [references]()                      | 工程实践入口，查技术栈、质量门禁、模板和常见坑         |
| [research](docs/research/README.md) | 研究入口，记录新技术、优秀 repo 和工程趋势判断         |
| [prompts](prompts/README.md)        | 提示词入口，复用和管理提示词资产                       |
| [skills](skills/README.md)          | 技能入口，复用可执行的 AI 能力模块                     |
| [tools](tools/README.md)            | 工具入口，使用 Codex 配置、转换工具和外部工具          |
| [assets](assets/README.md)          | 资源入口，查看外部资源、AI 引用语料和静态资产          |

### 界面还原规范（PySide6 重写蓝本）

从原型 `assets/hmi/`（入口 `index.html`，模块化工程）提炼，供 PySide6 像素级重写使用：

| 文档 | 用途 |
| :--- | :--- |
| [总则与设计令牌](docs/hmi/ui-restoration-spec.md) | 颜色/字号/间距/圆角令牌、窗口网格、字体系统、状态色、还原铁律 |
| [控件映射规范](docs/hmi/widget-qss-spec.md) | 每个控件的 HTML/CSS → PySide6 控件 → QSS 片段三列映射 |
| [页面布局规范](docs/hmi/page-layout-spec.md) | 8 页面 ASCII 布局图、区块/控件清单、数据字段、状态变体 |
| [交互规范](docs/hmi/interaction-spec.md) | 导航、串口台、勾选/确认状态机、PRD 编辑器、空/异常态 |
