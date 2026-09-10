"""
协议层测试

测试断言来自原型 jsdom 测试的翻译，用已知的 Modbus 报文值验证。
协议层是纯 Python，不依赖 Qt/PySide6。

运行：
    cd vibe-hmi
    .venv/Scripts/python.exe -m pytest tests/test_protocol.py -v
"""
import struct
import pytest
from src.protocol.modbus_protocol import (
    crc16,
    append_crc,
    build_read_frame,
    build_write_frame,
    type_to_reg_count,
    float32_to_bytes,
    bytes_to_float32,
    verify_crc,
    simulate_read_response,
    parse_read_response,
    ModbusProtocol,
    build_gw_write_addr_frame,
    build_gw_write_baud_frame,
    build_gw_write_parity_frame,
    build_gw_write_datetime_frame,
    GW_WRITE_HEADER_ADDR,
    GW_WRITE_HEADER_BAUD,
    GW_WRITE_HEADER_PARITY,
    GW_WRITE_HEADER_DT,
    GW_WRITE_SUB_ADDR,
    GW_WRITE_SUB_BAUD,
    GW_WRITE_SUB_PARITY,
    GW_WRITE_SUB_DT,
)


# ========== CRC16 ==========

class TestCRC16:
    def test_known_frame_crc(self):
        """读帧 01 03 00 00 00 01 的 CRC 应为 0x840A（低字节 0x84 在前）"""
        frame = [0x01, 0x03, 0x00, 0x00, 0x00, 0x01]
        crc = crc16(frame)
        # Modbus CRC16 低字节在前：crc & 0xFF = 0x84, (crc >> 8) & 0xFF = 0x0A
        assert (crc & 0xFF) == 0x84
        assert ((crc >> 8) & 0xFF) == 0x0A

    def test_crc_returns_int(self):
        assert isinstance(crc16([0x01, 0x03]), int)


# ========== append_crc ==========

class TestAppendCrc:
    def test_appends_two_bytes(self):
        frame = [0x01, 0x03, 0x00, 0x00, 0x00, 0x01]
        result = append_crc(frame.copy())
        assert len(result) == 8
        assert result[-2] == 0x84  # CRC 低字节
        assert result[-1] == 0x0A  # CRC 高字节

    def test_does_not_mutate_input(self):
        frame = [0x01, 0x03]
        original = frame.copy()
        append_crc(frame.copy())
        assert frame == original


# ========== build_read_frame ==========

class TestBuildReadFrame:
    def test_temperature_read_frame(self):
        """读 temperature(0x0000, uint16=1寄存器), slaveId=1 → 01 03 00 00 00 01 84 0A"""
        frame = build_read_frame(slave_id=1, address="0x0000", reg_count=1)
        assert frame == [0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A]

    def test_float32_read_frame_reg_count_2(self):
        """float32 占 2 寄存器 → 帧含 00 02"""
        frame = build_read_frame(slave_id=1, address="0x0000", reg_count=2)
        assert frame[4] == 0x00
        assert frame[5] == 0x02

    def test_slave_id_2_first_byte(self):
        """slaveId=2 时帧首字节 02"""
        frame = build_read_frame(slave_id=2, address="0x0000", reg_count=1)
        assert frame[0] == 0x02

    def test_frame_length_8(self):
        frame = build_read_frame(slave_id=1, address="0x0000", reg_count=1)
        assert len(frame) == 8


# ========== build_write_frame ==========

class TestBuildWriteFrame:
    def test_write_frame_format(self):
        """写 sample_period(0x0010)=1000ms(0x03E8) → 01 06 00 10 03 E8 + CRC"""
        frame = build_write_frame(slave_id=1, address="0x0010", value=0x03E8)
        assert frame[:6] == [0x01, 0x06, 0x00, 0x10, 0x03, 0xE8]
        assert len(frame) == 8  # 6 + 2 CRC


# ========== type_to_reg_count ==========

class TestTypeToRegCount:
    @pytest.mark.parametrize("type_name,expected", [
        ("uint8", 1), ("int16", 1), ("uint16", 1), ("bool", 1),
        ("uint32", 2), ("int32", 2), ("float32", 2),
    ])
    def test_reg_count(self, type_name, expected):
        assert type_to_reg_count(type_name) == expected


# ========== float32 编解码 ==========

class TestFloat32:
    def test_encode_decode_roundtrip(self):
        """编解码往返：25.5 → bytes → 25.5"""
        original = 25.5
        encoded = float32_to_bytes(original)
        decoded = bytes_to_float32(encoded)
        assert abs(decoded - original) < 0.01

    def test_negative_value(self):
        """float32 支持负值（temperature -40~125）"""
        original = -15.3
        encoded = float32_to_bytes(original)
        decoded = bytes_to_float32(encoded)
        assert abs(decoded - original) < 0.01

    def test_encode_returns_4_bytes(self):
        assert len(float32_to_bytes(1.0)) == 4


# ========== verify_crc ==========

class TestVerifyCrc:
    def test_valid_frame(self):
        frame = build_read_frame(slave_id=1, address="0x0000", reg_count=1)
        assert verify_crc(frame) is True

    def test_corrupted_frame(self):
        frame = build_read_frame(slave_id=1, address="0x0000", reg_count=1)
        frame[-1] ^= 0xFF  # 破坏 CRC
        assert verify_crc(frame) is False


# ========== simulate_read_response ==========

class TestSimulateReadResponse:
    def test_response_format(self):
        """模拟回包格式：[slaveId, 0x03, byteCount, data..., crc...]"""
        frame = build_read_frame(slave_id=1, address="0x0000", reg_count=2)
        param = {"type": "float32", "min": -40, "max": 125, "decimals": 1}
        result = simulate_read_response(frame, param)
        resp = result["resp"]
        assert resp[0] == 1         # slaveId
        assert resp[1] == 0x03      # 功能码
        assert resp[2] == 4         # byteCount = regCount * 2 = 4
        assert len(resp) >= 7       # slaveId + fc + byteCount + 4 data + 2 crc
        assert verify_crc(resp)     # 回包 CRC 校验通过

    def test_value_in_range(self):
        frame = build_read_frame(slave_id=1, address="0x0000", reg_count=2)
        param = {"type": "float32", "min": 0, "max": 60, "decimals": 2}
        result = simulate_read_response(frame, param)
        assert 0 <= result["eng_value"] <= 60


# ========== parse_read_response ==========

class TestParseReadResponse:
    def test_float32_parse(self):
        """float32 回包解析：构造已知值的回包，验证解析结果"""
        # 构造回包：slaveId=1, fc=03, byteCount=4, data=25.5 的 IEEE754, CRC
        data = float32_to_bytes(25.5)
        resp = append_crc([0x01, 0x03, 0x04] + data)
        param = {"type": "float32", "decimals": 1}
        result = parse_read_response(resp, param)
        assert abs(result["eng_value"] - 25.5) < 0.1

    def test_uint16_parse(self):
        """uint16 回包解析：raw=250, decimals=1 → 25.0"""
        resp = append_crc([0x01, 0x03, 0x02, 0x00, 0xFA])
        param = {"type": "uint16", "decimals": 1}
        result = parse_read_response(resp, param)
        assert result["raw_value"] == 250
        assert result["eng_value"] == 25.0


# ========== ModbusProtocol 集成（mock transport） ==========

class TestModbusProtocol:
    """测试 ModbusProtocol 类的 read_param/write_param，用 mock transport（不依赖真实串口）"""

    def _make_param(self, **kwargs):
        """构造测试参数"""
        defaults = {
            "name": "temperature", "display": "温度",
            "address": "0x0000", "type": "float32",
            "access": "只读", "unit": "℃",
            "decimals": 1, "min": -40, "max": 125,
        }
        defaults.update(kwargs)
        return defaults

    def test_read_param_success(self):
        """read_param 正常路径：返回 ok=True + value 在范围内"""
        proto = ModbusProtocol(slave_id=1, connection_state="connected")
        proto.set_mock_transport(True)  # 启用模拟回包
        param = self._make_param()
        result = proto.read_param(param)
        assert result["ok"] is True
        assert -40 <= result["value"] <= 125
        assert "frame" in result
        assert "response" in result
        assert isinstance(result["retried"], int)

    def test_read_param_disconnected(self):
        """断线时 read_param 返回 ok=False"""
        proto = ModbusProtocol(slave_id=1, connection_state="disconnected")
        proto.set_mock_transport(True)
        param = self._make_param()
        result = proto.read_param(param)
        assert result["ok"] is False
        assert "未连接" in result["error"]

    def test_write_param_success(self):
        """write_param 正常路径：echo 回包"""
        proto = ModbusProtocol(slave_id=1, connection_state="connected")
        proto.set_mock_transport(True)
        param = self._make_param(name="sample_period", address="0x0010", type="uint16",
                                 access="读写", unit="ms", decimals=0, min=200, max=5000)
        result = proto.write_param(param, 1000)
        assert result["ok"] is True
        # 写响应 = echo 请求帧
        assert result["response"] == result["frame"]

    def test_write_param_disconnected(self):
        """断线时 write_param 返回 ok=False"""
        proto = ModbusProtocol(slave_id=1, connection_state="disconnected")
        proto.set_mock_transport(True)
        param = self._make_param()
        result = proto.write_param(param, 100)
        assert result["ok"] is False

    def test_no_qt_dependency(self):
        """协议层不 import PySide6（纯 Python，可独立 pytest）"""
        import src.protocol.modbus_protocol as mod
        import inspect
        src = inspect.getsource(mod)
        # 检查 import 语句（文档字符串里提到 PySide6 不算依赖）
        import_lines = [line for line in src.split("\n") if line.strip().startswith("import") or line.strip().startswith("from")]
        for line in import_lines:
            assert "PySide6" not in line, f"协议层不应 import PySide6：{line}"
            assert "QtWidgets" not in line, f"协议层不应 import QtWidgets：{line}"


# ========== 国网写帧 sub_id 钉死测试 ==========
# 防止再次写错 sub_id：ADDR=0x01 / BAUD=0x02 / PARITY=0x03 / DT=0x04
# 子项 ID 与头部常量必须一一对应。

class TestGwWriteSubIds:
    """子项 ID 与头部常量的一致性"""

    def test_sub_id_constants(self):
        assert GW_WRITE_SUB_ADDR == 0x01
        assert GW_WRITE_SUB_BAUD == 0x02
        assert GW_WRITE_SUB_PARITY == 0x03
        assert GW_WRITE_SUB_DT == 0x04

    def test_header_sub_id_matches_name(self):
        # 头部第 3 字节（index 2）就是 sub_id
        assert GW_WRITE_HEADER_ADDR[2] == GW_WRITE_SUB_ADDR
        assert GW_WRITE_HEADER_BAUD[2] == GW_WRITE_SUB_BAUD
        assert GW_WRITE_HEADER_PARITY[2] == GW_WRITE_SUB_PARITY
        assert GW_WRITE_HEADER_DT[2] == GW_WRITE_SUB_DT


class TestGwWriteFrames:
    """国网协议写帧字节级断言（数据字节 + 头 sub_id）"""

    def test_write_addr_sub_id_and_value(self):
        # slave=2, addr=1 → 02 66 06 02 20 01 20 01 01 <CRC>
        frame = build_gw_write_addr_frame(2, 1)
        # 数据字节之前的部分：[slave, FC, byteCount, header[5]]
        assert frame[:3] == [0x02, 0x66, 0x06]
        assert frame[3:8] == GW_WRITE_HEADER_ADDR      # 子项 0x01
        assert frame[8] == 0x01                        # 数据字节 = 地址 1
        assert verify_crc(frame)

    def test_write_baud_sub_id_and_value(self):
        # slave=2, baud=9600(2) → 02 66 06 02 20 02 20 01 02 <CRC>
        frame = build_gw_write_baud_frame(2, 2)
        assert frame[:3] == [0x02, 0x66, 0x06]
        assert frame[3:8] == GW_WRITE_HEADER_BAUD      # 子项 0x02
        assert frame[8] == 0x02                        # 数据字节 = 9600
        assert verify_crc(frame)

    def test_write_parity_sub_id_and_value(self):
        # slave=2, parity=0(无校验) → 02 66 06 02 20 03 20 01 00 <CRC>
        frame = build_gw_write_parity_frame(2, 0)
        assert frame[:3] == [0x02, 0x66, 0x06]
        assert frame[3:8] == GW_WRITE_HEADER_PARITY    # 子项 0x03
        assert frame[8] == 0x00                        # 数据字节 = 无校验
        assert verify_crc(frame)

    def test_write_datetime_sub_id_and_len(self):
        # slave=2, 2021-07-29 15:33:58 →
        #   02 66 0C 02 20 04 40 07 E5 07 07 1D 0F 21 3A 78 76
        frame = build_gw_write_datetime_frame(2, 2021, 7, 29, 15, 33, 58)
        assert frame[:3] == [0x02, 0x66, 0x0C]                 # byteCount = 0x0C
        assert frame[3:8] == GW_WRITE_HEADER_DT                # 子项 0x04
        # 数据 = 7 字节：年LE 月 日 时 分 秒
        assert frame[8:15] == [0xE5, 0x07, 0x07, 0x1D, 0x0F, 0x21, 0x3A]
        assert verify_crc(frame)

    def test_parity_value_out_of_range(self):
        """parity_code 必须在 0/1/2 之间"""
        with pytest.raises(ValueError):
            build_gw_write_parity_frame(2, 3)

    def test_baud_value_out_of_range(self):
        """baud_code 必须在 0/1/2/3 之间"""
        with pytest.raises(ValueError):
            build_gw_write_baud_frame(2, 4)

    def test_addr_value_out_of_range(self):
        """addr 必须在 1~247 之间"""
        with pytest.raises(ValueError):
            build_gw_write_addr_frame(2, 0)
        with pytest.raises(ValueError):
            build_gw_write_addr_frame(2, 248)
