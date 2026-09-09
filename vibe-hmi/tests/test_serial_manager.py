"""
串口管理器统计测试

验证通信统计（丢包率等）按"连接会话"统计：新建连接清零，
连接失败/断开后保留上次会话数据。用替身串口模拟，不依赖真实硬件。

运行：
    cd vibe-hmi
    .venv/Scripts/python.exe -m pytest tests/test_serial_manager.py -v
"""
import pytest

import src.serial.serial_manager as sm_module
from src.serial.serial_manager import SerialManager


class FakeSerial:
    """替身串口：模拟一个已打开、永远无数据的 COM 口。"""

    def __init__(self, **kwargs):
        self.is_open = True
        self.in_waiting = 0
        self.port = kwargs.get("port")

    def read(self, n):
        return b""

    def write(self, data):
        return len(data)

    def flush(self):
        pass

    def close(self):
        self.is_open = False


class BrokenSerial:
    """替身串口：打开即失败（端口不存在）。"""

    def __init__(self, **kwargs):
        raise sm_module.serial.SerialException("could not open port 'COM_NONE'")


def _fake_bad_session(m: SerialManager):
    """伪造一段丢包率 100% 的历史会话（协议层每次请求失败都会累加这些计数器）。"""
    m.tx_frames = 100
    m.tx_failures = 100
    m.tx_bytes = 800
    m.rx_bytes = 0
    m.rx_frames = 0
    m.crc_errors = 3


class TestStatsResetOnReconnect:
    def test_reconnect_resets_stats(self, monkeypatch):
        """复现用户症状：上次连接丢包率 100%，断开重连后统计应清零。"""
        monkeypatch.setattr(sm_module.serial, "Serial", FakeSerial)
        m = SerialManager()
        assert m.connect("COM_FAKE")
        _fake_bad_session(m)

        m.disconnect()
        assert m.connect("COM_FAKE")

        stats = m.get_stats()
        assert stats["tx_frames"] == 0
        assert stats["tx_failures"] == 0
        assert stats["crc_errors"] == 0
        assert stats["tx_bytes"] == 0
        m.disconnect()

    def test_failed_connect_keeps_last_session_stats(self, monkeypatch):
        """连接失败不清零：上次会话的统计保留供查看。"""
        monkeypatch.setattr(sm_module.serial, "Serial", FakeSerial)
        m = SerialManager()
        assert m.connect("COM_FAKE")
        _fake_bad_session(m)
        m.disconnect()

        monkeypatch.setattr(sm_module.serial, "Serial", BrokenSerial)
        assert not m.connect("COM_NONE")

        stats = m.get_stats()
        assert stats["tx_frames"] == 100
        assert stats["tx_failures"] == 100
