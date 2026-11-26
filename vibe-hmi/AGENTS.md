# vibe-hmi Agent 手册

Modbus RTU 上位机（PySide6 6.11 + Python 3.11 + pyserial + SQLite + QtCharts）。
本目录是产品源码，改代码前先读仓库根目录 [AGENTS.md](../AGENTS.md)、[memory-bank/](../memory-bank/) 下的规划文档，
以及[决策与修改记录](../memory-bank/decision-log.md)。

## 常用命令

```bash
# 首次：创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 启动
.venv\Scripts\python.exe main.py

# 全量测试（协议层 / 串口 / 历史库 / 弹框 / 轻提示），改动后必须全部通过
.venv\Scripts\python.exe -m pytest tests/

# 打包（PyInstaller onedir，产物 dist/vibe-hmi/）
build.bat
```

## 架构约束

- 分层：UI 层（`src/pages/`）禁止直接访问串口；协议在 `src/protocol/`，串口在 `src/serial/`，轮询在 `src/workers/`，LLM 在 `src/ai/`
- `src/store.py` 是全局状态单例，运行时配置持久化到 `config/*.json`
- 历史采样与报警均存 `save/history.db`（SQLite，含按天过期策略，默认 90 天）
- 弹框统一走 `src/dialogs.py`，轻提示统一走 `src/toast.py`（2026-11-26 用户确认的设计）。文案惯例：标题说"是什么事"，
  说明说"该怎么办"；失败类把报文、异常等细节放进 `detail`。简短的成功反馈用轻提示，不打断操作

## 记录要求

- 本目录的每一次修改完成后，必须追加到仓库根目录的[决策与修改记录](../memory-bank/decision-log.md)，包括 Agent 自行做出的判断；细则见根目录 AGENTS.md 第 9 节

## 禁止事项

- 禁止提交 `config/model_config.json`（含 API Key）
- `config/`、`save/`、`history/`、`build/`、`dist/`、`.venv/` 均为运行时/构建产物，禁止提交
- 禁止删除或跳过 `tests/` 现有测试用例
- 禁止直接使用 `QMessageBox`，也不要新开独立的弹窗窗口：都用 `src/dialogs.py`（遮罩 + 卡片是主窗口的子控件）
- 提交前在仓库根目录运行 `make lint` 通过
