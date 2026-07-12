# 10 — 打包发布

**What to build:** 用 PyInstaller 把整个应用打包成单文件 exe（`--onefile --windowed`），目标 Windows 机器无需安装 Python 即可双击运行。打包前确认所有页面功能完整、协议层/AI 助手正常、资源文件（QSS/JSON 配置/图标）正确打包进 exe。验证打包后的程序在干净 Windows 环境能启动、连接设备、各页面可用。

**Blocked by:** 01, 02, 03, 04, 05, 06, 07, 08, 09 — 所有功能票（打包前全部功能必须完成）

**Status:** ready-for-agent

- [ ] PyInstaller 打包脚本（`--onefile --windowed --name multi-protocol-hmi`）
- [ ] 资源文件（style.qss / config JSON / 图标）正确打包进 exe
- [ ] 打包后的 exe 在干净 Windows 机器（无 Python）能双击启动
- [ ] 启动后主窗口正常显示，主题样式无丢失
- [ ] 协议层、串口连接、AI 助手在打包后正常工作
- [ ] 配置文件（params.json / model config）读写路径在打包后正确（exe 同级目录）
- [ ] exe 体积合理（记录大小，供优化参考）
