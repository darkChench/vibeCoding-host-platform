# 技术栈文档（memory-bank）

> 本文件固化 multi-protocol-hmi 上位机的技术选型与依据。
> 更新时间：2026-07-27。

## 1. 总体选型

| 层 | 选型 | 理由 |
| :--- | :--- | :--- |
| 桌面框架 | **PySide6 6.11 (Qt6)** | Qt 官方 Python 绑定，LGPL 商用免费；串口/Modbus 生态强；原生控件性能好 |
| 语言 | **Python 3.11** | pymodbus/pyserial 行业标配；开发效率高；现场调试易改 |
| 串口 | **pyserial 3.5** | 纯 Python，零编译，跨平台，行业事实标准 |
| Modbus | **自研协议层**（纯 Python） | CRC16/帧编解码/float32/批量读取，30 个 pytest 验证 |
| 数据处理 | **requests** | LLM API 调用（OpenAI/Anthropic 兼容） |
| 历史数据 | **SQLite（sqlite3 内置）** | Python 3 自带，无需安装，单文件持久化 |
| 图表 | **QtCharts** | Qt 原生集成，实时曲线渲染 |
| 打包 | **PyInstaller**（待实现） | 单 exe，离线安装 |
| AI/LLM | **OpenAI 兼容 + Anthropic 兼容** | 支持智谱 GLM / DeepSeek / 通义 / OpenAI / Moonshot |

## 2. 为什么是 PySide6 而不是 Electron / C++ Qt

| 维度 | PySide6 | Electron | C++ Qt |
| :--- | :--- | :--- | :--- |
| 串口/Modbus 生态 | ★★★★★ pymodbus+pyserial | ★★★ modbus-serial 轻维护 | ★★★★ QModbusClient |
| 开发效率 | ★★★★★ | ★★★★ | ★★ |
| 原型复用 | ★（HTML→Qt 重写） | ★★★★★（85%复用） | ★ |
| 内存/体积 | ★★★★ | ★★（Chromium 重） | ★★★★★ |
| 工业现场口碑 | ★★★★★ | ★★★ | ★★★★★ |

**结论**：本项目是 RS485 + Modbus RTU + 离线打包 + 工控机长期运行，PySide6 是甜点位。原型 HTML 只作交互蓝本，不复用代码。

## 3. 架构分层（已实现）

```text
PySide6 应用
├── UI 层（QWidget/QSS）          ← 12 个页面 + 主窗口框架
│   └── theme.py（设计令牌）+ style.py（全局 QSS）
├── 状态层（store.py）            ← 设备/参数/报警/模型配置/策略
│   └── 持久化到 config/*.json
├── 协议层（modbus_protocol.py）  ← CRC16/帧编解码/批量读取
│   └── 30 个 pytest 验证
├── 串口层（serial_manager.py）   ← pyserial 真实串口 + 模拟回退
├── AI 层（ai/）                  ← LLM 客户端 + 5 工具 + 后台线程
│   └── OpenAI/Anthropic 兼容
└── 数据层（history_db.py）       ← SQLite 历史数据存储
```

## 4. 关键依赖清单

| 依赖 | 版本 | 用途 |
| :--- | :--- | :--- |
| PySide6 | 6.11 | Qt GUI 框架（含 QtCharts/QtSvg） |
| pyserial | 3.5 | 串口访问 |
| requests | 2.34+ | LLM API 调用 |
| sqlite3 | 内置 | 历史数据（Python 3 自带） |
| pyinstaller | 6.0+ | 打包（待实现） |

注意：**未使用 pymodbus**，协议层是自研的纯 Python 实现（更可控、可测试）。pandas/openpyxl 仅在虚拟环境中安装但实际代码未使用（CSV 导出用 csv 标准库）。

## 5. 已确认的技术决策

| 问题 | 决策 |
| :--- | :--- |
| 图表选型 | **QtCharts**（已落地，原生集成，性能满足 360 点曲线） |
| LLM 接口 | **OpenAI 兼容 + Anthropic 兼容**（智谱 GLM 用 Anthropic 接口） |
| Python 版本 | **3.11** |
| 协议层 | **自研纯 Python**（非 pymodbus），30 个 pytest 验证 |
| 历史数据 | **SQLite**（非 CSV 文件） |
| 后台线程 | **QThread**（监控轮询 + LLM 请求） |
