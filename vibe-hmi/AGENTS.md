# vibe-hmi Agent 手册

Modbus RTU 上位机（PySide6 6.11 + Python 3.11 + pyserial + SQLite + QtCharts）。
本目录是产品源码，改代码前先读仓库根目录 [AGENTS.md](../AGENTS.md) 与 [memory-bank/](../memory-bank/) 三份规划文档。

## 常用命令

```bash
# 首次：创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 启动
.venv\Scripts\python.exe main.py

# 协议层测试（30 个 pytest，改动协议层必须全部通过）
.venv\Scripts\python.exe -m pytest tests/

# 打包（PyInstaller onedir，产物 dist/vibe-hmi/）
build.bat
```

## 架构约束

- 分层：UI 层（`src/pages/`）禁止直接访问串口；协议在 `src/protocol/`，串口在 `src/serial/`，轮询在 `src/workers/`，LLM 在 `src/ai/`
- `src/store.py` 是全局状态单例，运行时配置持久化到 `config/*.json`
- 历史采样与报警均存 `save/history.db`（SQLite，含按天过期策略，默认 90 天）

## 禁止事项

- 禁止提交 `config/model_config.json`（含 API Key）
- `config/`、`save/`、`history/`、`build/`、`dist/`、`.venv/` 均为运行时/构建产物，禁止提交
- 禁止删除或跳过 `tests/` 现有测试用例
- 提交前在仓库根目录运行 `make lint` 通过
