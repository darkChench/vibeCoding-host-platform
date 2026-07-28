# 01 — 工程骨架 + 主窗口框架

**What to build:** 运行 `python main.py` 能弹出 PySide6 主窗口，呈现 5 行 grid 框架（标题栏 / 菜单栏 / 工具栏 / 工作区 / 状态栏），主题令牌（颜色/字号/圆角/阴影）从原型 `tokens.css` 迁移为 `theme.py` 常量 + `style.qss`，视觉与原型一致。工具栏分两行（控件行 + 状态行）。

**Blocked by:** None — can start immediately.

**Status:** done

- [x] `vibe-hmi/main.py` 入口可运行，弹出主窗口
- [x] 虚拟环境 `.venv/` + `requirements.txt` 就绪（已完成，复用）
- [x] `theme.py` 含原型所有设计令牌（16 个基础色 + 散落色 + 字号5档 + 字重3档 + 圆角5档 + 控件基准高32px）
- [x] `style.qss` 应用全局主题，窗口背景/边框/圆角与原型一致
- [x] 主窗口 5 行 grid：标题栏 34px / 菜单栏 34px / 工具栏 auto / 工作区弹性 / 状态栏 28px
- [x] 标题栏含 app 图标 + 名称 + 居中副标题 + 三圆点
- [x] 工具栏两行：控件行（5 个下拉占位 + 连接/刷新按钮）+ 状态行（COM 状态/RX/TX/CRC/AI 状态）
- [x] 状态栏含保存路径 + 当前页指示
