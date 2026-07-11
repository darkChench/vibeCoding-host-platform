# 技术栈文档（memory-bank）

> 本文件固化 multi-protocol-hmi 上位机的技术选型与依据，供 AI 和开发者长期参考。
> 更新时间：2026-07-11。

## 1. 总体选型

| 层 | 选型 | 理由 |
| :--- | :--- | :--- |
| 桌面框架 | **PySide6 (Qt6)** | Qt 官方 Python 绑定，LGPL 商用免费；串口/Modbus/工业现场生态强；原生控件性能好 |
| 语言 | **Python 3.11+** | pymodbus/pyserial 行业标配；开发效率高；现场调试易改 |
| 串口 | **pyserial** | 纯 Python，零编译，跨平台，行业事实标准 |
| Modbus | **pymodbus** | 工业标准库，活跃维护，支持 RTU/TCP |
| 数据处理 | **pandas / openpyxl** | CSV/Excel 导出 |
| 打包 | **PyInstaller + Inno Setup** | 单 exe，离线安装 |
| 图表 | **QtCharts** 或 **pyqtgraph** | 实时曲线；QtCharts 原生集成，pyqtgraph 性能更强 |
| AI/LLM | **OpenAI 兼容 API**（通义/DeepSeek/智谱/Kimi/OpenAI） | function calling；5 家共用一套接口，换 base_url+key+model |

## 2. 为什么是 PySide6 而不是 Electron / C++ Qt

详见历史讨论结论，核心要点：

| 维度 | PySide6 | Electron | C++ Qt |
| :--- | :--- | :--- | :--- |
| 串口/Modbus 生态 | ★★★★★ pymodbus+pyserial | ★★★ modbus-serial 轻维护 | ★★★★ QModbusClient |
| 开发效率 | ★★★★★ | ★★★★ | ★★ |
| 原型复用 | ★（HTML→Qt 重写） | ★★★★★（85%复用） | ★ |
| 内存/体积 | ★★★★ | ★★（Chromium 重） | ★★★★★ |
| 工业现场口碑 | ★★★★★ | ★★★ | ★★★★★ |

**结论**：本项目是 RS485 + Modbus RTU + 离线打包 + 工控机长期运行 → PySide6 是甜点位。原型 HTML 只作交互蓝本，不复用代码。

## 3. 架构分层（对应原型的模块）

```text
PySide6 应用
├── UI 层（QWidget/QSS）          ← 对应原型 widgets.css + pages/*.js
│   └── 10 个页面 + 主窗口框架
├── 状态层（数据模型）             ← 对应原型 store.js
│   └── 参数表/报警/连接状态/对话历史
├── 协议层（pymodbus 封装）        ← 对应原型 modbusProtocol.js
│   └── readParam/writeParam（接口与原型一致）
├── AI 层（LLM + 工具）            ← 对应原型 aiTools.js + llmClient.js
│   └── function calling → 协议层
└── 通信层（pyserial）             ← 原型用模拟，PySide6 接真实串口
```

## 4. 关键依赖清单

| 依赖 | 版本 | 用途 | 安装 |
| :--- | :--- | :--- | :--- |
| PySide6 | 6.6+ | Qt GUI 框架 | `pip install PySide6` |
| pyserial | 3.5+ | 串口访问 | `pip install pyserial` |
| pymodbus | 3.6+ | Modbus 协议 | `pip install pymodbus` |
| pandas | 2.0+ | 数据导出 | `pip install pandas` |
| openpyxl | 3.1+ | Excel 导出 | `pip install openpyxl` |
| pyinstaller | 6.0+ | 打包 | `pip install pyinstaller` |

LLM 调用无需额外库（用 Qt 的 QNetworkAccessManager 或 requests 发 HTTP）。

## 5. 设计令牌迁移

原型 `assets/hmi/css/tokens.css` 的所有 CSS 变量，将迁移为 PySide6 的：

- Python 常量（`theme.py`，如 `PRIMARY = QColor("#0b6fb3")`）
- QSS 样式表（`style.qss`，直接用色值）

详见 `docs/hmi/widget-qss-spec.md` 的控件映射。

## 6. 协议层迁移

原型 `modbusProtocol.js` 的 `readParam`/`writeParam` 接口，在 PySide6 中**逐行可翻译**：

- `buildReadFrame` → 用 pymodbus 的 `ModbusTcpClient/SerialClient.read_holding_registers`
- `simulateReadResponse` → 替换为真实设备读写
- CRC16 / 报文注入串口日志 → 保留（pymodbus 自带 CRC，但日志注入逻辑复用）

## 7. AI 助手迁移

原型用模拟 LLM 响应（`llmClient.js` 关键词匹配）。PySide6 阶段：

- 取消 `llmClient.js` 注释块，启用真实 OpenAI 兼容 API 调用
- Qt 无 CORS 限制，可直接 fetch
- 工具定义（`aiTools.js` 的 TOOLS）几乎不变
- handler 改为调协议层（与原型一致）

## 8. 待确认

| 问题 | 影响 |
| :--- | :--- |
| 图表选 QtCharts 还是 pyqtgraph | 实时性能 vs 集成度，MVP 先用 QtCharts |
| LLM 是否本地化（Ollama） | 现场数据隐私；MVP 先用云 API |
| Python 版本 | 建议 3.11+（match 语法、性能）；待确认工控机环境 |
