# vibeCoding-host-platform：Modbus RTU 上位机

面向 Modbus RTU 嵌入式设备的 Windows 上位机，支持多设备管理、串口连接、实时数据采集与曲线监控、参数物模型配置、报警监控、历史数据查询（SQLite）和 AI 运维助手。

## 技术栈

PySide6 6.11 (Qt6) + Python 3.11 + pyserial + SQLite + QtCharts

## 快速开始

```bash
cd vibe-hmi
.venv\Scripts\python.exe main.py
```

## 入口导航

| 入口 | 说明 |
| :--- | :--- |
| [docs](docs/README.md) | 文档知识库总入口 |
| [docs/workFlow](docs/workFlow/README.md) | 开发工作流 |
| [docs/references](docs/references/) | 工程实践与质量门禁 |
| [tools](tools/README.md) | 工具配置 |
| [assets/hmi](assets/hmi/index.html) | HTML 原型（交互蓝本） |

## 界面还原规范（PySide6 重写蓝本）

| 文档 | 用途 |
| :--- | :--- |
| [总则与设计令牌](docs/hmi/ui-restoration-spec.md) | 颜色/字号/间距/圆角令牌、窗口网格 |
| [控件映射规范](docs/hmi/widget-qss-spec.md) | HTML/CSS → PySide6 控件 → QSS 映射 |
| [页面布局规范](docs/hmi/page-layout-spec.md) | 页面 ASCII 布局图、区块清单 |
| [交互规范](docs/hmi/interaction-spec.md) | 导航、状态机、协议层 |
| [组件样式参考](docs/hmi/component-style-reference.md) | 每个组件的最终渲染样式值 |
| [产品需求文档](docs/hmi/product-requirements.md) | 完整 PRD |

## 项目结构

```
vibe-hmi/
├── main.py                 # 入口
├── config/                 # 运行时配置（params/devices/policy/model_config）
├── save/                   # SQLite 历史数据库
├── src/
│   ├── theme.py            # 设计令牌
│   ├── style.py            # 全局 QSS
│   ├── store.py            # 全局状态管理
│   ├── protocol/           # Modbus RTU 协议层
│   ├── serial/             # pyserial 串口管理
│   ├── ai/                 # LLM 客户端 + 工具层
│   ├── workers/            # 后台线程
│   └── pages/              # 12 个页面
└── tests/                  # 协议层测试（30 个 pytest）
```
