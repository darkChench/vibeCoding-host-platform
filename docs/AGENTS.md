# Docs 目录 AI Agent 操作手册

本文件为 AI Agent 在 `docs/` 目录下的操作提供约束清单。

---

## 1、允许的操作

- 读取、修改 `docs/` 下所有文档
- 新增设计规范、布局文档、交互文档
- 更新已有文档以反映代码变更

## 2、禁止的操作

- 删除已有文档（除非任务明确要求）
- 在文档中写入未经验证的猜测内容（用 TODO 标注）
- 修改 `docs/hmi/product-requirements.md` 的验收标准（需用户确认）

## 3、文档同步规则

**任何功能/命令/配置变化必须同步更新对应文档：**

| 变更类型 | 需更新的文档 |
|:---|:---|
| 新增/修改页面布局 | `hmi/page-layout-spec.md` |
| 新增/修改控件样式 | `hmi/widget-qss-spec.md` + `hmi/component-style-reference.md` |
| 新增/修改交互逻辑 | `hmi/interaction-spec.md` |
| 修改设计 token | `hmi/ui-restoration-spec.md` |
| 新增/修改 Agent 工作流 | `agents/` 下对应文档 |

## 4、格式要求

- 文档使用中文
- 代码块标注语言（```python / ```text / ```json）
- ASCII 布局图用等宽字体代码块
- 表格用 Markdown 标准语法
- 路径用反引号包裹（如 `src/pages/monitor_page.py`）
