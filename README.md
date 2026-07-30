# vibeCoding-host-platform：Modbus RTU 上位机

面向 Modbus RTU 嵌入式设备的 Windows 上位机，支持多设备管理、串口连接、实时数据采集与曲线监控、参数物模型配置、报警监控、历史数据查询（SQLite）和 AI 运维助手。

## 技术栈

PySide6 6.11 (Qt6) + Python 3.11 + pyserial + SQLite + QtCharts

## 快速开始

```bash
cd vibe-hmi
.venv\Scripts\python.exe main.py
```

## 打包发布（生成无依赖 exe）

将上位机打包成可在**无 Python 环境**的 Windows PC 上直接运行的程序。

```bash
cd vibe-hmi
build.bat
```

产物：`vibe-hmi/dist/vibe-hmi/`（约 316 MB），双击 `vibe-hmi.exe` 即可启动。

**分发方式**：把整个 `dist/vibe-hmi/` 文件夹压缩成 zip，拷贝到目标电脑解压，
双击 `vibe-hmi.exe` 运行。目标机无需安装 Python 或任何依赖。

**用户数据位置**（首次运行在 exe 同级自动创建）：

| 目录 | 内容 |
| :--- | :--- |
| `config/` | 设备/参数/策略/模型配置（JSON） |
| `save/` | 历史采样数据库（SQLite） |
| `history/` | 串口日志（TXT） |

如需重置应用，删除这三个目录后重启即可。

> 打包说明：PyInstaller onedir 模式，自动收集 PySide6/QtCharts/QtSvg/pyserial，
> 排除未使用的 pandas/pymodbus/WebEngine 等大模块以压缩体积。
> 详见 `vibe-hmi/vibe-hmi.spec` 和 `vibe-hmi/build.bat`。

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

```text
vibe-hmi/
├── main.py                 # 入口
├── build.bat               # 一键打包脚本（PyInstaller）
├── vibe-hmi.spec           # PyInstaller 打包配置
├── config/                 # 运行时配置（params/devices/policy/model_config）
├── save/                   # SQLite 历史数据库
├── src/
│   ├── paths.py            # 路径解析（开发/打包双模式感知）
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
