# 实施计划（memory-bank）

> 本文件是 multi-protocol-hmi 从原型到 PySide6 产品的实施路线与任务拆解。
> 更新时间：2026-07-27。

## 1. 总体路线

```text
阶段 0（已完成）：HTML 原型 + 规范文档 + 协议层 + AI 助手原型
阶段 1（已完成）：PySide6 工程骨架 + 主窗口 + 主题令牌
阶段 2（已完成）：逐页迁移（12 个页面全部实现）
阶段 3（已完成）：协议层接入真实 pyserial（Modbus RTU + 模拟回退）
阶段 4（已完成）：AI 助手接入真实 LLM（OpenAI/Anthropic 兼容）
阶段 5（待实现）：打包发布
```

## 2. 当前里程碑

| 里程碑 | 内容 | 状态 |
| :--- | :--- | :--- |
| M0 原型完成 | HTML 原型 10 页 + 规范文档 + 协议层 + AI 助手 | ✅ 完成 |
| M1 骨架搭建 | vibe-hmi/ 工程结构 + 主窗口 + 主题 | ✅ 完成 |
| M2 核心 3 页 | 串口连接 + 实时监控 + 参数配置 | ✅ 完成 |
| M3 协议层落地 | Modbus RTU 真实收发 + 模拟回退 | ✅ 完成 |
| M4 AI 助手落地 | 真实 LLM function calling（5 工具） | ✅ 完成 |
| M5 多设备架构 | 每设备独立参数表 + 设备管理 | ✅ 完成 |
| M6 历史数据 | SQLite + 查询 + QtCharts + CSV 导出 | ✅ 完成 |
| M7 打包发布 | PyInstaller 打 exe | ⬜ 待实现 |

## 3. 阶段 1：PySide6 工程骨架（已完成）

工程结构实际落地：

```text
vibe-hmi/
├── main.py                       # 入口
├── config/                       # 运行时配置（params/devices/policy/model_config/history）
├── save/                         # SQLite 历史数据库
├── history/                      # 串口日志
├── assets/icons/                 # SVG 图标
├── src/
│   ├── theme.py                  # 设计令牌（48 个 QColor）
│   ├── style.py                  # 全局 QSS（build_qss()）
│   ├── store.py                  # 全局状态管理（设备/参数/报警/模型配置）
│   ├── icons.py                  # SVG 图标渲染（QSvgRenderer）
│   ├── page_registry.py          # 页面注册表（12 页）
│   ├── sidebar.py                # 侧边栏导航
│   ├── main_area.py              # 主区（tabs + QStackedWidget）
│   ├── main_window.py            # 主窗口（菜单栏/工具栏/状态栏）
│   ├── history_db.py             # SQLite 历史数据库
│   ├── protocol/modbus_protocol.py  # Modbus RTU 协议层
│   ├── serial/serial_manager.py    # pyserial 串口管理器
│   ├── workers/poll_worker.py      # 后台轮询线程
│   ├── ai/
│   │   ├── llm_client.py         # LLM 客户端（OpenAI/Anthropic 兼容）
│   │   ├── ai_tools.py           # AI 工具层（5 工具 + handler）
│   │   └── llm_worker.py         # LLM 后台线程
│   └── pages/                    # 12 个页面
└── tests/test_protocol.py        # 协议层测试（30 个 pytest）
```

## 4. 阶段 2：逐页迁移（已完成）

| 页面 | 文件 | 状态 |
| :--- | :--- | :--- |
| 设备总览 | overview_page.py | ✅ |
| 设备管理 | device_page.py | ✅ |
| 串口连接 | serial_page.py | ✅ |
| 实时监控 | monitor_page.py | ✅ |
| 参数配置 | params_page.py | ✅ |
| 报警记录 | alarms_page.py | ✅ |
| 历史数据 | history_page.py | ✅ |
| 状态策略 | status_policy_page.py | ✅ |
| 系统设置 | settings_page.py | ✅ |
| 模型配置 | model_config_page.py | ✅ |
| AI 助手 | ai_assistant_page.py | ✅ |
| 网关配置 | gw_config_page.py | ✅ |

## 5. 阶段 3：协议层落地（已完成）

- 纯 Python 协议层（CRC16/帧编解码/float32），30 个 pytest 全通过
- pyserial 真实串口 + 模拟回退
- 批量读取（连续地址合并）
- 十进制/十六进制地址支持

## 6. 阶段 4：AI 助手落地（已完成）

- OpenAI 兼容 + Anthropic 兼容（智谱 GLM）
- 5 个工具：read_sensor / read_all_sensors / get_alarms / get_trend / get_device_status
- 后台线程调 LLM（QThread）
- Markdown 渲染助手回复

## 7. 阶段 7：打包发布（待实现）

```bash
pyinstaller --onefile --windowed --name multi-protocol-hmi main.py
```

验收：在目标 Windows 机器双击 exe 可运行，无需 Python 环境。

## 8. 已解决的风险

| 风险 | 状态 | 实际处理 |
| :--- | :--- | :--- |
| temperature 负值问题 | ✅ 已解决 | 协议层支持 int16/float32 负值 |
| float32 字节序 | ✅ 已解决 | Big-Endian 实现 + 长度容错 |
| LLM 云 API 现场可用性 | ✅ 已解决 | 智谱/DeepSeek/OpenAI 三套接口支持 |
| 工控机无 Python 环境 | ⬜ 待打包 | PyInstaller 打包（阶段 7） |
