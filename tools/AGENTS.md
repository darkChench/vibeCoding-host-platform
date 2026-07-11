# tools/external/ 目录 Agent 指南

本目录用于收纳 **外部工具/第三方项目**（含 Git submodule），保持“主仓库资产”和“外部依赖”边界清晰、可审计、可更新。

## 目录结构（约定）

```text
tools/external/
├── AGENTS.md                         # 本文件（目录级行为准则）
├── README.md                         # 外部工具索引
```

## 当前软链接显示

```text

```

## 操作规范

### 允许

- 新增外部依赖（优先 Git submodule，确保可复现）
- 更新 submodule 指针（明确记录上游来源与用途）
- 用相对软链接把 `tools/external/` 下的事实来源暴露到其它目录，软链接目标必须仍在仓库内
- 为已复制进主仓库的外部源码建立清退计划：上游 URL、保留理由、迁移方式、验证命令

### 禁止 / 不推荐

- 直接复制粘贴大型第三方仓库内容到主仓库（优先 submodule）
- 将 submodule 替换为本地绝对路径软链接（会导致他人环境不可用）
- 提交第三方仓库的构建产物、生成物、运行时二进制或缓存目录
- 在主仓库直接魔改第三方源码快照；需要改造时先 fork，再以 submodule 指向 fork

## 仓库表达决策

1. **完整外部仓库**：优先使用 `git submodule`，主仓库只记录 commit 指针。
2. **同仓多入口展示**：使用相对软链接，例如 `skills/<name> -> ../tools/external/<name>`。
3. **项目内小工具**：只有在无上游、体量小、与本项目强耦合时才直接追踪源码。
4. **生成输出**：默认不跟踪；若必须保留样例，只提交最小样例和生成说明。
5. **普通目录**：`html-tools-main/`、`my-nvim/`、`MCPlayerTransfer/`、`XHS-image-to-PDF-conversion/` 当前作为小体量工具快照保留；确认上游 URL 后再转 submodule。
6. **清退触发**：普通目录出现体量膨胀、生成物混入、上游仓库明确或需要频繁升级时，必须优先转 submodule 或迁出主仓库。
7. **语言统计**：`tools/external/**` 已在根目录 `.gitattributes` 标记为 `linguist-vendored`，避免外部工具源码污染主仓库语言占比。
