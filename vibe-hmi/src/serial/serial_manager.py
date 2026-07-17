"""
串口管理器

封装 pyserial 的连接/断开/读写，提供统一的串口通信接口。
- 真实串口：pyserial 打开 COM 口，后台线程持续读取
- 模拟模式：无设备时自动回退，发送/接收走模拟逻辑（和监控页协议层模拟一致）

全局单例 serial_manager，供工具栏连接操作、串口页终端、协议层 transport 共用。
"""
import time
import random

import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, Signal, QThread

from ..protocol.modbus_protocol import (
    build_read_frame, build_write_frame, simulate_read_response,
    type_to_reg_count, verify_crc, CONFIG,
)


class ReadThread(QThread):
    """串口后台读线程：持续读取串口数据，收到发 data_received 信号"""
    data_received = Signal(bytes)

    def __init__(self, ser: serial.Serial):
        super().__init__()
        self._serial = ser
        self._running = True

    def run(self):
        while self._running and self._serial and self._serial.is_open:
            try:
                n = self._serial.in_waiting
                if n > 0:
                    data = self._serial.read(n)
                    if data:
                        self.data_received.emit(data)
                else:
                    self.msleep(20)  # 无数据时短暂休眠，降低 CPU
            except Exception:
                break

    def stop(self):
        self._running = False
        self.quit()
        self.wait(2000)


class SerialManager(QObject):
    """串口管理器：连接/断开/读写/枚举端口

    真实串口模式：pyserial 打开端口，ReadThread 持续读取。
    模拟模式（无设备）：connect 时打开失败自动回退，send 时生成模拟回包。
    """

    # 信号
    data_received = Signal(bytes)        # 收到串口数据（真实模式）
    connection_changed = Signal(bool)    # 连接状态变化（bool = 是否连接）

    def __init__(self):
        super().__init__()
        self._serial: serial.Serial | None = None
        self._reader: ReadThread | None = None
        self._is_mock = False
        self._is_connected = False
        # 统计
        self.tx_bytes = 0
        self.rx_bytes = 0
        self.tx_frames = 0
        self.rx_frames = 0
        self.crc_errors = 0

    # ===== 连接管理 =====

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    def connect(self, port: str, baudrate: int = 115200, bytesize: int = 8,
                parity: str = "N", stopbits: float = 1, timeout: float = 0.1) -> bool:
        """打开串口。失败时回退模拟模式。"""
        # 先断开旧连接
        self.disconnect()

        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=timeout,
            )
            # 启动读线程
            self._reader = ReadThread(self._serial)
            self._reader.data_received.connect(self._on_data_received)
            self._reader.start()
            self._is_mock = False
            self._is_connected = True
            self.connection_changed.emit(True)
            return True
        except Exception:
            # 打开失败 → 模拟模式
            self._serial = None
            self._is_mock = True
            self._is_connected = True
            self.connection_changed.emit(True)
            return True

    def disconnect(self):
        """断开连接"""
        if self._reader:
            self._reader.stop()
            self._reader = None
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None
        was_connected = self._is_connected
        self._is_mock = False
        self._is_connected = False
        if was_connected:
            self.connection_changed.emit(False)

    def refresh_ports(self) -> list[str]:
        """枚举可用串口列表"""
        ports = serial.tools.list_ports.comports()
        return [p.device for p in sorted(ports, key=lambda x: x.device)]

    # ===== 收发 =====

    def send(self, data: bytes) -> bool:
        """发送数据。返回是否成功。

        真实模式：写入串口。
        模拟模式：不写串口，回包在 read_response 中生成。
        """
        if not self._is_connected:
            return False
        self.tx_bytes += len(data)
        self.tx_frames += 1
        if self._is_mock:
            return True
        try:
            self._serial.write(data)
            return True
        except Exception:
            return False

    def transact(self, request: bytes) -> bytes | None:
        """完整收发：发送请求帧 → 等待响应帧 → 返回响应字节。

        真实模式：write + read 等待回包。
        模拟模式：解析请求帧生成模拟响应（含延迟）。
        超时返回 None。
        """
        if not self._is_connected:
            return None

        # 发送请求
        self.send(request)

        if self._is_mock:
            # 模拟回包
            return self._mock_response(request)

        # 真实模式：等待响应
        try:
            timeout_ms = CONFIG["timeout_ms"]
            deadline = time.time() + timeout_ms / 1000 * (CONFIG["max_retries"] + 1)
            buf = b""
            while time.time() < deadline:
                n = self._serial.in_waiting
                if n > 0:
                    buf += self._serial.read(n)
                    # Modbus 最小响应 5 字节
                    if len(buf) >= 5:
                        break
                time.sleep(0.01)
            if buf:
                self.rx_bytes += len(buf)
                self.rx_frames += 1
            return buf if buf else None
        except Exception:
            return None

    def _mock_response(self, request: bytes) -> bytes | None:
        """模拟模式：根据请求帧生成 Modbus 响应帧"""
        req = list(request)
        if len(req) < 4:
            return None

        # 模拟延迟
        time.sleep(0.05 + random.random() * 0.05)

        slave_id = req[0]
        fc = req[1] if len(req) > 1 else 0x03

        if fc == 0x03:
            # 读保持寄存器：从请求取地址 + 寄存器数
            addr = (req[2] << 8) | req[3]
            reg_count = (req[4] << 8) | req[5] if len(req) >= 6 else 1
            byte_count = reg_count * 2
            # 生成随机数据
            data_bytes = []
            for _ in range(byte_count):
                data_bytes.append(random.randint(0, 255))
            resp = [slave_id, fc, byte_count] + data_bytes
        elif fc == 0x06:
            # 写单寄存器：echo 请求
            resp = req.copy()
        else:
            resp = req.copy()

        # 加 CRC
        from ..protocol.modbus_protocol import append_crc
        resp = append_crc(resp)
        resp_bytes = bytes(resp)
        self.rx_bytes += len(resp_bytes)
        self.rx_frames += 1
        return resp_bytes

    def _on_data_received(self, data: bytes):
        """读线程收到数据的回调（真实模式）"""
        self.rx_bytes += len(data)
        self.rx_frames += 1
        self.data_received.emit(data)

    # ===== 统计 =====

    def get_stats(self) -> dict:
        """获取通信统计"""
        return {
            "tx_bytes": self.tx_bytes,
            "rx_bytes": self.rx_bytes,
            "tx_frames": self.tx_frames,
            "rx_frames": self.rx_frames,
            "crc_errors": self.crc_errors,
        }

    def reset_stats(self):
        """重置统计"""
        self.tx_bytes = 0
        self.rx_bytes = 0
        self.tx_frames = 0
        self.rx_frames = 0
        self.crc_errors = 0


# 全局单例
serial_manager = SerialManager()
