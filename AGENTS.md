# Repository Guidelines

本文件为 AI Agent 提供项目操作手册与约束清单，确保 Agent 行为可控、可复现。

---

## 1、Mission & Scope（目标与边界）

### 允许的操作

- 读取、修改顶层文档：`README.md`、`AGENTS.md`、`CONTRIBUTING.md` 等
- 读取、修改 `docs/`、`prompts/`、`skills/`、`tools/config/`、`tools/external/` 下的文档与代码
- 新增/修改提示词、技能、文档
- 提交符合规范的 commit

### 禁止的操作

- 修改 `.github/workflows/` 中的 CI 配置（除非任务明确要求）)（先不实现）
- 修改 `LICENSE`、`CODE_OF_CONDUCT.md`
- 在代码中硬编码密钥、Token 或敏感凭证
- 未经确认的大范围重构

### 敏感区域（禁止自动修改）

- `.github/workflows/*.yml` - CI/CD 配置（如存在）先不实现）
- `.env*` 文件（如存在）

---

## 2、Golden Path（推荐执行路径）

```
# 1. 拉取最新代码
git pull --rebase origin main

# 2. 初始化外部仓库指针
git submodule update --init --recursive

# 3. 运行 lint 检查
make lint

# 4. 执行修改任务
# ...

# 5. 再次 lint 验证
make lint

# 6. 提交变更
git add -A
git commit -m "feat|fix|docs|chore: scope - summary"
git push origin main
```

## 3、Must-Run Commands（必须执行的命令清单）

### 环境要求

- Node.js 22+（通过 `npx --yes markdownlint-cli@0.48.0` 运行固定版本 Markdown lint）
- Git

### 核心命令

| 命令          | 用途                | 前置条件                                                     |
| ------------- | ------------------- | ------------------------------------------------------------ |
| `make help` | 列出所有 Make 目标  | 无                                                           |
| `make lint` | 校验全仓库 Markdown | Node.js 22+；通过 `npx --yes markdownlint-cli@0.48.0` 执行 |
| `make test` | 执行本地质量门禁    | Node.js 22+、Python 3                                        |

## 4、Code Change Rules（修改约束）

### 架构原则

- 保持根目录扁平，避免巨石文件
- 三层内容架构：`docs/` (知识) → `prompts/` (指令) → `skills/` (能力)

### 模块边界

- `docs/` - 中文知识库（方法论/入门/实战/资源）
- `prompts/` - 提示词入口
- `skills/` - 可复用技能库（每个子目录一个 Skill）
- `tools/config/` - 工具与开发配置（例如 Codex CLI）
- `tools/external/` - 外部工具与依赖（含 Git submodule）

### 依赖添加规则

- 新增工具或库时记录安装方式、最小版本与来源
- 外部依赖来源记录在 `tools/external/` 目录下
- 引入第三方脚本需标明许可证与来源

### 禁止行为

- 禁止"顺手重构/大范围改动"除非任务明确要求
- 禁止删除现有测试用例（除非任务要求）
- 禁止在代码中硬编码敏感信息

## 5、Style & Quality（风格与质量标准）

### 格式化工具

- Markdown：`Makefile` 固定调用 `markdownlint-cli@0.48.0`（通过 `make lint` 执行）
- CI 自动检查：`.github/workflows/ci.yml （先不实现））`

### 命名约定

- 文档、注释、日志使用中文
- 代码符号统一英文且语义直白
- 文件名小写加中划线或下划线

### 缩进与排版

- 全仓保持空格缩进（2 或 4 空格不混用）
- 行宽控制在 120 列内

### 设计品味

- 优先消除分支与重复
- 函数单一职责且短小

---

## 6、Project Map（项目结构速览）

```
.
├── README.md                    # 项目主文档
├── AGENTS.md                    # AI Agent 行为准则（本文件）
```

### 关键入口文件

- `README.md` - 项目主文档，面向人类开发者
- `AGENTS.md` - AI Agent 操作手册（本文件）

## 7、Common Pitfalls（常见坑与修复）

| col1                  | col2                                                               | 修复                                                                                                             |
| --------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| `make lint` 失败    | Node.js 不可用、npx 无法拉取 markdownlint-cli 或 Markdown 规则违规 | 先确认 `node -v` 为 22+，再运行 `make lint`                                                                  |
| CI markdown-lint 失败 | Markdown 规则违规或本地未按 `.github/lint_config.json` 校验      | 运行 `make lint`，按输出修复对应 Markdown                                                                      |
| CI link-checker 失败  | 文档中存在失效链接，或官方外链在 GitHub runner 上网络/TLS 不稳定   | 先本地验证链接；真实失效则修复 Markdown，runner 不稳定则优先调整 `.lychee.toml` 的重试、超时、并发或精确排除项 |

## 8、PR / Commit Rules（提交与 CI 规则）

### Commit 规范

遵循简化 Conventional Commits：

```
feat|fix|docs|chore|refactor|test: scope - summary
```

示例：

- `docs: prompts - add new coding prompt`
- `feat: skills - add custom skill`
- `fix: readme - correct broken link`

### PR 必填内容

- 变更摘要
- 动机或关联 Issue
- 测试与验证步骤

### CI 检查项

1. `markdown-lint` - Markdown 格式检查
2. `check local markdown links and anchors` - 仓库内相对链接与锚点检查
3. `check markdown details and summaries` - Markdown 折叠块结构检查
4. `check docs README structure` - docs README 标准块顺序、目录入口和重复锚点检查
5. `check required directory README and AGENTS files` - 仓库自有目录 README/AGENTS 覆盖检查
6. `check metadata paths and anchors` - metadata 路径与锚点检查
7. `check llms and AI citation paths and anchors` - llms 与 AI 引用语料路径和锚点检查
8. `check modern enterprise architecture kit` - 现代企业架构 starter kit schema 与示例一致性检查
9. `link-checker` - 链接有效性检查

### 提交前清单

- [ ] 运行 `make lint` 通过
- [ ] 更新对应文档
- [ ] 确认不携带临时文件或机密数据

## 9. Documentation Sync Rule（强制同步规则）

**任何功能/命令/配置/目录/工作流变化必须同步更新：**

- `README.md` - 面向人类开发者
- `AGENTS.md` - 面向 AI Agent（本文件）

**不确定的内容用 TODO 标注，不允许猜测。**

## 10、Memory Bank（记忆库）

Memory-Bank目录中，存放所有核心规划文档，为AI提供持久、稳定的上下文。

* `product-requirements.md`:  **产品需求文档** 。由AI根据用户输入的想法生成初稿。
* `tech-stack.md`:  **技术栈文档** 。由AI推荐并论证。
* `implementation-plan.md`:  **实施计划** 。由AI将需求分解为具体的、可验证的步骤。

## 11、Agent skills

### Issue tracker

Issue 和 spec 以本地 markdown 文件形式存放在 `.scratch/<feature>/`。详见 `docs/agents/issue-tracker.md`。

### Triage labels

使用五个默认 triage 角色（needs-triage / needs-info / ready-for-agent / ready-for-human / wontfix）。详见 `docs/agents/triage-labels.md`。

### Domain docs

单仓库布局（single-context）：根目录 `CONTEXT.md` + `docs/adr/`。详见 `docs/agents/domain.md`。
