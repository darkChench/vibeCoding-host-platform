# vibe-hmi 上位机

Modbus RTU 嵌入式设备的 Windows 桌面 HMI 应用。

技术栈：PySide6 6.11 (Qt6) + Python 3.11 + pyserial + SQLite + QtCharts

## 开发运行

```bash
# 首次：创建虚拟环境并装依赖
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 启动
.venv\Scripts\python.exe main.py
```

## 打包发布

把应用打包成可在无 Python 环境的电脑上直接运行的 exe：

```bash
build.bat
```

产物：`dist/vibe-hmi/vibe-hmi.exe`（onedir 模式，约 375 MB）。

把整个 `dist/vibe-hmi/` 压缩成 zip 拷给目标机，解压后双击 exe 即可运行。首次运行会在 exe 同级自动创建 `config/`（设备配置）、`save/`（历史数据库）、`history/`（串口日志）三个用户数据目录。

详见仓库根目录 [README.md](../README.md) 的「打包发布」章节。

## 目录结构

| 路径 | 作用 |
| :--- | :--- |
| `main.py` | 程序入口 |
| `build.bat` | 一键打包脚本 |
| `vibe-hmi.spec` | PyInstaller 打包配置 |
| `src/` | 源码（store / protocol / serial / ai / pages） |
| `config/` | 运行时配置（JSON，自动生成） |
| `save/` | 历史采样数据库（SQLite，自动生成） |
| `history/` | 串口日志（TXT，自动生成） |
| `assets/icons/` | 图标资源 |
| `tests/` | 协议层 pytest 测试 |
