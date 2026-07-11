# 实施计划（memory-bank）

> 本文件是 multi-protocol-hmi 从原型到 PySide6 产品的实施路线与任务拆解。
> 更新时间：2026-07-11。

## 1. 总体路线

```text
阶段 0（已完成）：HTML 原型 + 规范文档 + 协议层 + AI 助手
阶段 1（下一步）：PySide6 工程骨架 + 主窗口 + 主题令牌
阶段 2：逐页迁移（10 个页面）
阶段 3：协议层接入真实 pymodbus
阶段 4：AI 助手接入真实 LLM
阶段 5：打包发布
```

## 2. 当前里程碑

| 里程碑 | 内容 | 状态 |
| :--- | :--- | :--- |
| M0 原型完成 | HTML 原型 10 页 + 规范文档 + 协议层 + AI 助手 | ✅ 完成 |
| M1 骨架搭建 | vibe-hmi/ 工程结构 + 主窗口 + 主题 | ⬜ 下一步 |
| M2 核心 3 页 | 串口连接 + 实时监控 + 参数配置 | ⬜ |
| M3 协议层落地 | pymodbus 接真实设备 | ⬜ |
| M4 AI 助手落地 | 真实 LLM function calling | ⬜ |
| M5 打包发布 | PyInstaller + Inno Setup | ⬜ |

## 3. 阶段 1：PySide6 工程骨架（下一步详细任务）

目标：`vibe-hmi/` 从空目录变成可运行的 PySide6 工程，主窗口框架搭好，主题令牌落地。

### 3.1 目录结构

```text
vibe-hmi/
├── README.md
├── AGENTS.md
├── requirements.txt              # PySide6/pyserial/pymodbus/pandas/openpyxl
├── pyproject.toml                # 或 setup.py
├── main.py                       # 入口
├── src/
│   ├── theme.py                  # 设计令牌（颜色/字号常量）
│   ├── style.qss                 # 全局 QSS（迁移自 tokens.css）
│   ├── app.py                    # QApplication 初始化
│   ├── main_window.py            # 主窗口（5 行 grid 框架）
│   ├── pages/                    # 10 个页面（逐页迁移）
│   ├── components/               # 复用组件（下拉/终端/图表）
│   ├── protocol/                 # 协议层（modbusProtocol.py）
│   ├── ai/                       # AI 助手（tools/llm_client）
│   └── store.py                  # 状态层
└── tests/
```

### 3.2 任务拆解（M1）

| 任务 | 输入 | 输出 | 验收 |
| :--- | :--- | :--- | :--- |
| 1.1 工程初始化 | requirements.txt | `pip install` 可跑 | `python main.py` 弹出空窗口 |
| 1.2 主题令牌 | tokens.css | theme.py + style.qss | QSS 颜色与原型一致 |
| 1.3 主窗口框架 | layout.css 的 5 行 grid | main_window.py | 标题栏/菜单栏/工具栏/工作区/状态栏 |
| 1.4 侧边栏导航 | 原型 tree 结构 | sidebar.py | 设备/数据/AI 三组可点击 |
| 1.5 页面路由 | app.js showPage | router.py | 点击侧栏切换页面 |

## 4. 阶段 2：逐页迁移（M2 核心 3 页先行）

按价值排序：

| 顺序 | 页面 | 复杂度 | 依赖 |
| :--- | :--- | :--- | :--- |
| 1 | 参数配置（物模型 CRUD） | 中 | store |
| 2 | 实时监控（曲线+协议层） | 高 | 协议层 + 图表 |
| 3 | 串口连接（控制台+手动收发） | 高 | pyserial |
| 4 | 首页总览 | 低 | 无 |
| 5 | 报警记录 | 中 | store |
| 6 | 历史数据 | 中 | 图表 + 导出 |
| 7 | 系统设置 | 低 | 无 |
| 8 | 状态策略 | 低 | 无 |
| 9 | 模型配置 | 中 | store |
| 10 | AI 助手 | 高 | LLM + 协议层 |

## 5. 阶段 3：协议层落地（M3）

原型的 `modbusProtocol.js` → `protocol/modbus_protocol.py`：

| 原型方法 | PySide6 实现 |
| :--- | :--- |
| `buildReadFrame` | `client.read_holding_registers(addr, count, slave)` |
| `simulateReadResponse` | 删除，用真实设备响应 |
| `parseReadResponse` | pymodbus 返回结果直接取 `.registers` |
| `appendCrc` | pymodbus 自动处理 |
| 日志注入 | 信号槽 → 串口页控制台 |

## 6. 阶段 4：AI 助手落地（M4）

- 启用 `llmClient.js` 注释块的真实调用逻辑
- 用 `requests` 或 `QNetworkAccessManager` 调 OpenAI 兼容 API
- 工具定义（TOOLS）不变
- handler 调协议层（与原型一致）

## 7. 阶段 5：打包（M5）

```bash
pyinstaller --onefile --windowed --name multi-protocol-hmi main.py
# 或用 Inno Setup 做安装包
```

验收：在目标 Windows 机器双击 exe 可运行，无需 Python 环境。

## 8. 风险与待确认

| 风险 | 影响 | 处理 |
| :--- | :--- | :--- |
| temperature uint16 负值问题 | 协议层数据错 | 改 int16 或调 min |
| uint32/float32 字节序 | 多类型设备出错 | 当前不用，后续按需配 |
| LLM 云 API 现场可用性 | AI 助手不可用 | 降级为模拟或本地 Ollama |
| 工控机无 Python 环境 | 无法运行 | PyInstaller 打包解决 |
