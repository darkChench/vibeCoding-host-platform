# 03 — 协议层 + pytest 测试

**What to build:** Modbus RTU 协议层（`modbus_protocol.py`），把参数表翻译成真实报文：`read_param(param)` 生成读请求帧（功能码 03 + CRC16）、`write_param(param, value)` 生成写请求帧（功能码 06）。含 CRC16（多项式 0xA001，低字节在前）、float32 IEEE754 编解码、type→寄存器数量映射、异常处理（断线检测/超时重试/CRC 校验失败/异常注入报警）。协议层是纯 Python，**不依赖 Qt**，用 pytest 测试。原型阶段用 mock transport（模拟回包），PySide6 阶段替换为 pymodbus 真实收发，接口不变。

**Blocked by:** 02 — 侧边栏导航 + 页面路由（协议层本身无 UI 依赖，但需要挂在工程结构里）

**Status:** ready-for-agent

- [ ] `read_param(param)` 返回 `{ok, value, raw, frame, response, retried}`
- [ ] `write_param(param, eng_value)` 返回 `{ok, frame, response, retried}`
- [ ] CRC16 算法正确：读帧 `01 03 00 00 00 01 84 0A`（temperature slaveId=1）
- [ ] float32 IEEE754 编解码正确（支持负值，如 temperature -40~125）
- [ ] type→寄存器数量：float32/uint32/int32=2，uint16/int16/uint8/bool=1
- [ ] 断线检测：connectionState != connected 时返回 ok:false
- [ ] 超时重试：max_retries=1，重试后仍失败返回 error
- [ ] CRC 校验失败：回包 CRC 错误重试，仍失败注入报警
- [ ] pytest 全过（断言逻辑从原型 jsdom 测试翻译）
- [ ] 协议层不 import PySide6，可独立 `pytest` 运行
