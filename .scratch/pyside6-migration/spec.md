# Spec: PySide6 上位机迁移（pyside6-migration）

> 来源：memory-bank 三份文档 + HTML 原型（`assets/hmi/`）+ 规范文档（`docs/hmi/`）。
> 本 spec 覆盖 M1~M5 全程：从空目录到可打包的 PySide6 桌面应用。

## Problem Statement

现场工程师需要一套 Windows 上位机，通过 RS485 串口连接 Modbus RTU 嵌入式设备，完成实时数据采集、参数物模型配置、控制下发、报警监控和历史查询。现有上位机不满足按设备定义不同物模型、不能直观调试报文、缺乏 AI 辅助运维能力。目前已有完整的 HTML 交互原型和 QSS 级还原规范，但真正的桌面应用（`vibe-hmi/`）还是空目录，需要用 PySide6 实现出来。

## Solution

用 PySide6 (Qt6) 将 HTML 原型迁移为原生 Windows 桌面应用。原型定义的 10 个页面、设计令牌、Modbus 协议层、AI 助手能力，全部按规范文档（`docs/hmi/`）还原成 Qt 实现。协议层接真实 pymodbus + pyserial，AI 助手接真实 LLM（OpenAI 兼容 API），最终用 PyInstaller 打包成离线 exe。

## User Stories

1. 作为操作员，我想打开上位机看到设备总览（在线状态/告警/快捷操作），以便一眼掌握现场情况。
2. 作为操作员，我想配置串口参数（串口号/波特率/数据位/校验位/停止位）并连接，以便与 RS485 设备通信。
3. 作为操作员，我想在串口控制台看到实时收发的 HEX 报文，以便确认通信是否正常。
4. 作为操作员，我想在串口控制台手动发送 HEX/ASCII 帧（含行结束符、自动发送），以便调试设备协议。
5. 作为操作员，我想看到采样参数的实时值和单位，以便监控设备运行状态。
6. 作为操作员，我想看到采样参数的短周期趋势曲线，以便发现异常趋势。
7. 作为操作员，我想点击曲线 chip 显隐对应曲线，以便聚焦关注的点位。
8. 作为工程师，我想增删改查参数物模型（地址/类型/权限/单位/范围），以便适配不同寄存器布局。
9. 作为工程师，我想设置当前设备的从站地址（1-247），以便协议层正确组帧。
10. 作为工程师，我想按分类（全部/采样参数/配置参数）筛选参数表，以便快速定位。
11. 作为工程师，我想在参数表单里得到校验反馈（地址格式/范围/必填），以免配置错误。
12. 作为操作员，我想查看报警记录并按级别/状态筛选，以便追溯异常。
13. 作为操作员，我想确认未确认报警（单条/全部），以便记录处理轨迹。
14. 作为管理者，我想按时间范围查询历史采样数据并看趋势，以便分析长期变化。
15. 作为管理者，我想把历史查询结果导出为 CSV，以便离线分析。
16. 作为操作员，我想配置离线判定策略（无通讯超时时间），以便设备总览自动反映离线。
17. 作为操作员，我想在系统设置里看到软件信息和维护操作（清理日志/导出诊断），以便日常维护。
18. 作为工程师，我想通过自然语言对话操作设备（"查温度""有哪些报警"），以便不记命令也能工作。
19. 作为工程师，我想配置 AI 助手使用的 LLM 提供商（OpenAI/通义/DeepSeek/智谱/Kimi），以便接入选定的模型。
20. 作为工程师，我想测试 LLM 连接是否可用，以便确认配置正确。
21. 作为操作员，我想在串口未连接时收到明确提示（发送禁用/控制台提示），以免误操作。
22. 作为操作员，我想在通信异常（超时/CRC 错误）时看到报警自动产生，以便及时发现通信故障。
23. 作为操作员，我想在协议层自动收发报文时也能在串口日志看到 TX/RX 流，以便掌握后台通信。
24. 作为操作员，我想双击 exe 就能运行（无需装 Python），以便在现场工控机部署。

## Implementation Decisions

### 架构分层

```text
UI 层（QWidget + QSS）       ← 对应原型 pages/*.js + widgets.css
状态层（数据模型/QAbstractItemModel） ← 对应原型 store.js
协议层（modbus_protocol.py）  ← 对应原型 modbusProtocol.js（接口逐行可翻译）
AI 层（LLM + 工具函数）       ← 对应原型 aiTools.js + llmClient.js
通信层（pymodbus + pyserial） ← 原型用模拟，PySide6 接真实串口
```

### 协议层接口（与原型一致，PySide6 逐行翻译）

- `read_param(param) -> Result`：生成读请求帧 → pymodbus read_holding_registers → 解析回包 → 返回工程值。
- `write_param(param, eng_value) -> Result`：生成写请求帧 → pymodbus write_register → echo 校验。
- 含断线检测、超时重试（max_retries=1）、CRC 二次校验、异常注入报警。
- CRC16 复用原型算法（多项式 0xA001，低字节在前）。
- float32 用 IEEE754 编解码（DataView 等价：Python 用 struct.pack/unpack '>f'）。

### type → Modbus 映射（已固化的决策）

- float32 / uint32 / int32 → 2 寄存器（4 字节）
- uint16 / int16 / uint8 / bool → 1 寄存器（2 字节）
- 功能码：读 03（Read Holding），写 06（Write Single）
- float32 地址须 2 对齐（temperature 0x0000-0x0001，pressure 0x0002-0x0003）

### 设计令牌迁移

原型 `assets/hmi/css/tokens.css` 的 CSS 变量 → `src/theme.py`（Python 常量）+ `src/style.qss`（QSS，直接用色值）。详见 `docs/hmi/widget-qss-spec.md` 的三列映射（HTML/CSS → PySide6 控件 → QSS 片段）。

### 主窗口网格

5 行 grid（34/34/50/1fr/28，标题栏/菜单栏/工具栏/工作区/状态栏），详见 `docs/hmi/ui-restoration-spec.md` §4。工具栏分两行（控件行 + 状态行），状态行独占。

### 页面迁移顺序（按价值）

参数配置 → 实时监控 → 串口连接 → 首页总览 → 报警记录 → 历史数据 → 系统设置 → 状态策略 → 模型配置 → AI 助手。

### AI 助手落地

启用原型 `llmClient.js` 注释块的真实调用逻辑，用 requests/QNetworkAccessManager 调 OpenAI 兼容 `/chat/completions`，tools 参数 4 个工具的 JSON Schema。Qt 无 CORS 限制，可直接 HTTP。handler 调协议层。

### 打包

PyInstaller `--onefile --windowed --name multi-protocol-hmi main.py`。

## Testing Decisions

### 主 seam：协议层（单一 seam）

- **测什么**：`modbus_protocol.py` 的 `read_param` / `write_param` / CRC16 / float32 编解码 / 异常路径（超时/CRC错/断线）。
- **怎么测**：pytest，纯 Python 无 Qt 依赖。协议层不 import PySide6，保证可独立测试。
- **优先复用**：原型 jsdom 测试的断言逻辑可直接翻译成 pytest（如"读帧=01 03 00 00 00 01 84 0A"、"raw=250 decimals=1 → 25.0"）。
- **只测外部行为**：测 read_param 返回的 value/frame/response，不测内部私有函数实现细节。
- **异常路径**：断线返回 ok:false、超时重试后报错、CRC 错重试、异常注入报警记录。

### 不纳入自动化测试

- UI 交互（Qt UI 测试脆弱、慢、维护成本高）——靠手动验收（像原型阶段那样）。
- 真实串口通信（依赖物理设备）——协议层用 mock transport 测逻辑，真实设备靠现场联调。

## Out of Scope

- 不实现 TCP 通信（仅 RS485 串口）。
- 不做多设备型号区分（当前单一设备型号）。
- 不做用户权限系统（PRD §10 暂不实现）。
- 不做云端数据同步（纯本地）。
- 不写 UI 自动化测试（QTest）。
- 不处理 uint32/int32 字节序可配（当前 float32 用 Big-Endian 固定，后续按需）。
- 不在 M1 实现全部 10 页（M1 只搭骨架+主窗口+导航，逐页在后续 milestone）。

## Further Notes

- **原型不复用代码**：HTML/JS/CSS 只作交互蓝本，PySide6 用 Python 重写。规范文档是真相源。
- **temperature uint16 负值问题已解决**：原型阶段已改为 float32，可表示负值。
- **memory-bank 是项目蓝本**：`product-requirements.md` / `tech-stack.md` / `implementation-plan.md` 已固化。
- **规范文档已含 QSS 级映射**：`docs/hmi/widget-qss-spec.md` 每个控件都给了 HTML/CSS → PySide6 → QSS 三列，实现时直接查。
- **协议层是内部逻辑**：报文格式不让用户碰，参数表是页面可配的配置，串口手动发送是独立调试路径。
