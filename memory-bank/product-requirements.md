# 产品需求文档（memory-bank）

> 本文件是 multi-protocol-hmi 上位机的核心需求固化。
> 与 `docs/hmi/product-requirements.md`（完整版）保持同步，这里只保留精简摘要。
> 更新时间：2026-07-27。

## 1. 文档信息

| 项目 | 内容 |
| :--- | :--- |
| 产品名称 | multi-protocol-hmi |
| 文档版本 | v1.0.0（与 docs/hmi/product-requirements.md 同步） |
| 编写人 | chench |
| 关联仓库 | https://github.com/darkChench/vibeCoding-host-platform |
| 技术栈 | PySide6 6.11 + Python 3.11 + pyserial + SQLite |
| 完整 PRD | `docs/hmi/product-requirements.md` |

## 2. 一句话定义

面向 Modbus RTU 嵌入式设备的 Windows 上位机，支持多设备管理、串口连接、实时数据采集、参数物模型配置、报警监控、历史数据查询（SQLite），并集成 AI 运维助手用自然语言读取设备数据。

## 3. 功能模块（12 个页面，全部已实现）

| 页面 | 功能 | 状态 |
| :--- | :--- | :--- |
| 设备总览 | metric + 快捷卡 + 设备列表 | ✅ |
| 设备管理 | 多设备 CRUD（每设备独立参数表） | ✅ |
| 串口连接 | 控制台 + HEX/ASCII 收发 + 自动发送 + 历史 | ✅ |
| 实时监控 | metric + QtCharts 趋势曲线 + 4 档时间范围 | ✅ |
| 参数配置 | 参数 CRUD + 设备切换 + 曲线展示字段 | ✅ |
| 报警记录 | 报警表 + 确认状态机 + CSV 导出 | ✅ |
| 历史数据 | SQLite 查询 + 快捷时间范围 + QtCharts + CSV | ✅ |
| 状态策略 | 离线判定配置 + 预览（持久化） | ✅ |
| 系统设置 | 键值表 + 运行时长 + 维护操作 | ✅ |
| 模型配置 | LLM 提供商 CRUD + 预设 + 测试连接 | ✅ |
| AI 助手 | 对话 + function calling（5 工具） | ✅ |
| 网关配置 | 网关参数配置 | ✅ |

## 4. 技术约束

- UI 层禁止直接访问串口（分层）
- 协议层是内部逻辑，报文格式不让用户碰
- 参数表是页面可配，协议层据此组帧
- API Key 本地存储，不提交 Git
- 打包发布前必须通过质量门禁

## 5. 验收标准

| 编号 | 验收项 | 状态 |
| :--- | :--- | :--- |
| A-001 | 串口连接 | ✅ |
| A-002 | 实时采集 | ✅ |
| A-003 | 参数配置 | ✅ |
| A-004 | 报警确认 | ✅ |
| A-005 | 历史导出 | ✅ |
| A-006 | 设备管理 | ✅ |
| A-007 | AI 助手 | ✅ |
| A-008 | 串口调试 | ✅ |
| A-009 | 打包安装 | ⬜ 待实现 |

## 6. 已解决的问题

| 问题 | 状态 | 实际处理 |
| :--- | :--- | :--- |
| temperature 负值 | ✅ | 协议层支持 int16/float32 负值 |
| float32 字节序 | ✅ | Big-Endian + 长度容错 |
| 真实 LLM 接入 | ✅ | OpenAI/Anthropic 兼容（智谱/DeepSeek） |
| 多设备支持 | ✅ | 每设备独立参数表 + 设备管理页 |
| 历史数据存储 | ✅ | SQLite 持久化 |
