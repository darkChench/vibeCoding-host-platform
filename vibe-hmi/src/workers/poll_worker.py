"""
轮询后台线程

监控页用 PollWorker(QThread) 在后台线程循环调用协议层 read_param，
避免 UI 线程因模拟串口延迟（50-100ms/次）而卡顿。

协议层 read_param 是同步阻塞的，放子线程跑；采样完成后发 tick 信号回主线程。
后续接真实串口时，只需替换 ModbusProtocol 的 transport，本线程结构不变。
"""
from PySide6.QtCore import QThread, Signal

from ..protocol.modbus_protocol import ModbusProtocol


class PollWorker(QThread):
    """后台轮询所有采样参数，每轮发一次 tick 信号。

    tick 载荷：{param_name: {"ok": bool, "value": float, "error": str}}
    """

    tick = Signal(dict)

    def __init__(self, params: list[dict], slave_id: int = 1, interval_ms: int = 1000):
        super().__init__()
        self._params = params
        self._interval_ms = interval_ms
        self._running = True
        # 原型阶段用模拟回包；真实串口阶段换 transport
        self._protocol = ModbusProtocol(slave_id=slave_id, connection_state="connected")

    def update_params(self, params: list[dict]):
        """参数表增删后更新轮询目标（线程安全：list 引用替换）"""
        self._params = params

    def stop(self):
        """请求停止并等待线程退出"""
        self._running = False
        self.quit()
        self.wait(2000)

    def run(self):
        while self._running:
            result = {}
            for p in self._params:
                if not self._running:
                    break
                r = self._protocol.read_param(p)
                result[p["name"]] = {
                    "ok": r["ok"],
                    "value": r.get("value", 0.0),
                    "error": r.get("error", ""),
                }
            if self._running:
                self.tick.emit(result)
            # 按配置间隔等待，拆成 100ms 片段便于快速响应 stop
            for _ in range(max(1, self._interval_ms // 100)):
                if not self._running:
                    break
                self.msleep(100)
