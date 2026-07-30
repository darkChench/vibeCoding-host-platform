"""
Modbus RTU 协议层

迁移自原型 assets/hmi/js/components/modbusProtocol.js。
把参数表（address/type/access）翻译成真实 Modbus RTU 报文（含 CRC16）。

这是"内部逻辑"——报文格式固定，不让用户碰。
纯 Python，不依赖 PySide6/Qt，可独立 pytest。

PySide6 阶段：把 simulate_read_response / transact_once 替换为
pymodbus 的 client.read_holding_registers / write_register，接口不变。
"""
import struct
import random
import time

# Modbus 功能码
FC_READ_HOLDING = 0x03
FC_WRITE_SINGLE = 0x06

# 协议层配置
CONFIG = {
    "timeout_ms": 100,       # 超时阈值
    "max_retries": 1,        # 重试次数
    "no_response_rate": 0.0,  # 模拟无响应概率（测试时设 0）
    "crc_error_rate": 0.0,    # 模拟 CRC 错误概率（测试时设 0）
}


def type_to_reg_count(type_name: str) -> int:
    """type → Modbus 寄存器数量"""
    if type_name in ("uint8", "int8", "uint16", "int16", "bool"):
        return 1
    if type_name in ("uint32", "int32", "float32"):
        return 2
    return 1


def crc16(data: list[int]) -> int:
    """Modbus RTU CRC16（多项式 0xA001，初值 0xFFFF，低字节在前）"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def append_crc(frame: list[int]) -> list[int]:
    """给帧追加 CRC16（低字节在前）"""
    crc = crc16(frame)
    frame.append(crc & 0xFF)
    frame.append((crc >> 8) & 0xFF)
    return frame


def verify_crc(data: list[int]) -> bool:
    """校验回包 CRC：末两字节（LE）应等于前面字节的 crc16"""
    if len(data) < 3:
        return False
    payload = data[:-2]
    crc = crc16(payload)
    return (crc & 0xFF) == data[-2] and ((crc >> 8) & 0xFF) == data[-1]


def parse_address(address: str) -> int:
    """解析寄存器地址。

    支持两种格式：
    - "0x03E8" / "0X03E8" → 16 进制
    - "1000" → 十进制（默认）
    """
    address = address.strip()
    if address.lower().startswith("0x"):
        return int(address, 16)
    return int(address, 10)


def build_read_frame(slave_id: int, address: str, reg_count: int) -> list[int]:
    """生成读保持寄存器请求帧（功能码 03）"""
    addr = parse_address(address)
    frame = [
        slave_id & 0xFF,
        FC_READ_HOLDING,
        (addr >> 8) & 0xFF, addr & 0xFF,
        (reg_count >> 8) & 0xFF, reg_count & 0xFF,
    ]
    return append_crc(frame)


def build_write_frame(slave_id: int, address: str, value: int) -> list[int]:
    """生成写单寄存器请求帧（功能码 06）"""
    addr = parse_address(address)
    frame = [
        slave_id & 0xFF,
        FC_WRITE_SINGLE,
        (addr >> 8) & 0xFF, addr & 0xFF,
        (value >> 8) & 0xFF, value & 0xFF,
    ]
    return append_crc(frame)


def float32_to_bytes(value: float) -> list[int]:
    """float32 → 4 字节（IEEE754 Big-Endian，高字在前）"""
    return list(struct.pack(">f", value))


def bytes_to_float32(data: list[int]) -> float:
    """4 字节 → float32（IEEE754 Big-Endian）"""
    return struct.unpack(">f", bytes(data))[0]


def simulate_read_response(frame: list[int], param: dict) -> dict:
    """模拟设备响应读请求（功能码 03）。

    在参数 min/max 范围内生成随机工程值，按 type 编码进响应帧。
    """
    slave_id = frame[0]
    reg_count = type_to_reg_count(param["type"])
    byte_count = reg_count * 2

    # min/max 可能为空字符串（参数页选填），需容错
    def _safe_float(val, default):
        try:
            return float(val) if val not in ("", None) else default
        except (ValueError, TypeError):
            return default
    min_val = _safe_float(param.get("min", 0), 0)
    max_val = _safe_float(param.get("max", 100), 100)
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    eng_value = min_val + random.random() * (max_val - min_val)

    if param["type"] == "float32":
        data_bytes = float32_to_bytes(eng_value)
        raw_value = eng_value
    elif reg_count == 1:
        decimals = int(param.get("decimals", 0))
        scale = 10 ** decimals
        raw_value = round(eng_value * scale)
        data_bytes = [(raw_value >> 8) & 0xFF, raw_value & 0xFF]
    else:
        decimals = int(param.get("decimals", 0))
        scale = 10 ** decimals
        raw_value = round(eng_value * scale)
        data_bytes = [
            (raw_value >> 24) & 0xFF, (raw_value >> 16) & 0xFF,
            (raw_value >> 8) & 0xFF, raw_value & 0xFF,
        ]

    resp = append_crc([slave_id, FC_READ_HOLDING, byte_count] + data_bytes)
    return {"resp": resp, "raw_value": raw_value, "eng_value": eng_value}


def parse_read_response(resp: list[int], param: dict) -> dict:
    """解析读响应，提取原始值并按 decimals 缩放为工程值。"""
    reg_count = type_to_reg_count(param["type"])
    data_bytes = resp[3:3 + reg_count * 2]
    decimals = int(param.get("decimals", 0))

    # 数据长度不足时补零（真实设备可能返回不完整的帧）
    expected = reg_count * 2
    if len(data_bytes) < expected:
        data_bytes = list(data_bytes) + [0] * (expected - len(data_bytes))

    if param["type"] == "float32":
        raw_value = bytes_to_float32(data_bytes)
        eng_value = round(raw_value, decimals)
    elif reg_count == 1:
        raw_value = (data_bytes[0] << 8) | data_bytes[1]
        eng_value = round(raw_value / (10 ** decimals), decimals)
    else:
        raw_value = (data_bytes[0] << 24) | (data_bytes[1] << 16) | \
                    (data_bytes[2] << 8) | data_bytes[3]
        eng_value = round(raw_value / (10 ** decimals), decimals)

    return {"raw_value": raw_value, "eng_value": eng_value}


class ModbusProtocol:
    """协议层主类：read_param / write_param，含异常处理。

    原型阶段用 mock transport（模拟回包）。
    PySide6 阶段替换为 pymodbus 真实收发，接口不变。
    """

    def __init__(self, slave_id: int = 1, connection_state: str = "connected"):
        self.slave_id = slave_id
        self.connection_state = connection_state
        self._use_mock = False  # mock transport 开关
        self._serial_manager = None  # 串口管理器（注入后走真实/模拟串口）
        self._log_callback = None  # 日志回调（接串口控制台，由调用方注入）

    def set_mock_transport(self, enabled: bool):
        """启用/禁用模拟回包（原型阶段用 True，PySide6 阶段用真实 pymodbus）"""
        self._use_mock = enabled

    def set_serial_transport(self, serial_manager):
        """注入串口管理器，协议层收发走 serial_manager.transact()"""
        self._serial_manager = serial_manager

    def set_log_callback(self, callback):
        """注入日志回调：callback(direction, label, content) → None"""
        self._log_callback = callback

    def _log(self, direction: str, label: str, content: str):
        if self._log_callback:
            self._log_callback(direction, label, content)

    def _transact_once(self, frame: list[int], param: dict | None, is_write: bool) -> dict:
        """单次收发。

        优先级：serial_manager（真实/模拟串口）> _use_mock（纯模拟）。
        可能返回：ok / timeout / crc_error。
        """
        hex_frame = " ".join(f"{b:02X}" for b in frame)
        self._log("tx", "TX", hex_frame)

        # 有串口管理器 → 走真实/模拟串口收发
        if self._serial_manager and self._serial_manager.is_connected:
            resp_bytes = self._serial_manager.transact(bytes(frame))
            if resp_bytes is None or len(resp_bytes) == 0:
                self._log("rx", "TIMEOUT", f"等待 {CONFIG['timeout_ms']}ms 无响应")
                # 累计请求失败次数（用于稳定的累计丢包率）
                self._serial_manager.tx_failures += 1
                return {"type": "timeout"}
            resp = list(resp_bytes)
            hex_resp = " ".join(f"{b:02X}" for b in resp)
            self._log("rx", "RX", hex_resp)
            # CRC 校验
            if not verify_crc(resp):
                self._log("rx", "CRC", "回包校验失败")
                # 累加 CRC 错误统计（让通信统计与诊断日志一致）
                self._serial_manager.crc_errors += 1
                self._serial_manager.tx_failures += 1
                return {"type": "crc_error", "resp": resp}
            return {"type": "ok", "resp": resp}

        # 纯模拟模式（无串口管理器）
        # 模拟无响应
        if random.random() < CONFIG["no_response_rate"]:
            time.sleep(CONFIG["timeout_ms"] / 1000)
            return {"type": "timeout"}

        # 模拟延迟
        time.sleep(0.05 + random.random() * 0.05)

        # 生成回包
        if is_write:
            resp = frame.copy()  # echo
        else:
            resp = simulate_read_response(frame, param)["resp"]

        # 模拟 CRC 错误
        if random.random() < CONFIG["crc_error_rate"]:
            resp = resp.copy()
            resp[-1] ^= 0xFF
            self._log("rx", "RX", " ".join(f"{b:02X}" for b in resp))
            return {"type": "crc_error", "resp": resp}

        self._log("rx", "RX", " ".join(f"{b:02X}" for b in resp))
        return {"type": "ok", "resp": resp}

    def read_param(self, param: dict) -> dict:
        """读取单个参数。含断线检测、超时重试、CRC 校验。"""
        if self.connection_state != "connected":
            return {"ok": False, "error": "串口未连接", "retried": 0}

        reg_count = type_to_reg_count(param["type"])
        last_error = ""
        retried = 0

        for attempt in range(CONFIG["max_retries"] + 1):
            frame = build_read_frame(self.slave_id, param["address"], reg_count)
            result = self._transact_once(frame, param, is_write=False)

            if result["type"] == "ok":
                if not verify_crc(result["resp"]):
                    last_error = "CRC 校验失败"
                    self._log("rx", "CRC", "回包校验失败")
                    # 累加 CRC 错误统计（防御性二次校验，与通信统计保持一致）
                    if self._serial_manager:
                        self._serial_manager.crc_errors += 1
                    if attempt < CONFIG["max_retries"]:
                        retried += 1
                        continue
                    return {"ok": False, "error": last_error, "retried": retried}

                parsed = parse_read_response(result["resp"], param)
                return {
                    "ok": True,
                    "value": parsed["eng_value"],
                    "raw": parsed["raw_value"],
                    "frame": frame,
                    "response": result["resp"],
                    "retried": retried,
                }

            if result["type"] == "timeout":
                last_error = "从站无响应（超时）"
                self._log("rx", "TIMEOUT", f"等待 {CONFIG['timeout_ms']}ms 无响应")
                if attempt < CONFIG["max_retries"]:
                    retried += 1
                    continue
                return {"ok": False, "error": last_error, "retried": retried}

            if result["type"] == "crc_error":
                last_error = "回包 CRC 错误"
                if attempt < CONFIG["max_retries"]:
                    retried += 1
                    continue
                return {"ok": False, "error": last_error, "retried": retried}

        return {"ok": False, "error": last_error or "未知错误", "retried": retried}

    def read_params_batch(self, params: list[dict]) -> dict:
        """批量读取多个参数。连续地址的参数合并成一次 Modbus 读请求。

        将参数按地址排序，连续地址（或间隔很小）的参数分成一组，
        每组只发一条读请求（功能码 03），从响应中按偏移提取每个参数值。
        大幅减少报文数量（4 个参数从 4 条请求 → 可能只 1~2 条）。

        返回 {param_name: {"ok": bool, "value": float, "error": str}}
        """
        if self.connection_state != "connected":
            return {p["name"]: {"ok": False, "value": 0.0, "error": "串口未连接"} for p in params}

        if not params:
            return {}

        # 按地址排序
        sorted_params = sorted(params, key=lambda p: parse_address(p["address"]))

        # 分组：地址连续（前一个的末地址 >= 后一个的起始地址 - 间隔阈值）的合并
        # 间隔阈值：允许小间隔（如 2 寄存器以内）也合并，减少请求次数
        GAP_THRESHOLD = 4  # 寄存器间隔 <= 4 也合并
        groups: list[list[dict]] = []
        for p in sorted_params:
            addr = parse_address(p["address"])
            regs = type_to_reg_count(p["type"])
            end = addr + regs
            if groups:
                last_p = groups[-1][-1]
                last_end = parse_address(last_p["address"]) + type_to_reg_count(last_p["type"])
                if addr - last_end <= GAP_THRESHOLD:
                    groups[-1].append(p)
                    continue
            groups.append([p])

        # 每组发一次读请求
        result = {}
        for idx, group in enumerate(groups):
            # 两组之间间隔 300ms（避免连续请求太快导致设备处理不过来）
            if idx > 0:
                time.sleep(0.3)
            start_addr = parse_address(group[0]["address"])
            last_p = group[-1]
            total_regs = parse_address(last_p["address"]) + type_to_reg_count(last_p["type"]) - start_addr

            # Modbus 单次最多读 125 寄存器
            total_regs = min(total_regs, 125)

            frame = build_read_frame(self.slave_id, group[0]["address"], total_regs)
            transact_result = self._transact_once(frame, None, is_write=False)

            if transact_result["type"] != "ok":
                # 整组失败
                err = "超时" if transact_result["type"] == "timeout" else "CRC 错误"
                for p in group:
                    result[p["name"]] = {"ok": False, "value": 0.0, "error": err}
                continue

            resp = transact_result["resp"]
            if not verify_crc(resp):
                for p in group:
                    result[p["name"]] = {"ok": False, "value": 0.0, "error": "CRC 校验失败"}
                continue

            # 从响应数据区提取每个参数的值
            # 响应格式：[slave, FC, byteCount, data...]
            resp_data = resp[3:]  # 去掉 slave/FC/byteCount
            for p in group:
                p_addr = parse_address(p["address"])
                offset = p_addr - start_addr  # 寄存器偏移
                byte_offset = offset * 2      # 字节偏移
                reg_count = type_to_reg_count(p["type"])
                # 构造伪响应给 parse_read_response（它需要 [slave, FC, byteCount, data...]）
                p_data = resp_data[byte_offset:byte_offset + reg_count * 2]
                if len(p_data) < reg_count * 2:
                    result[p["name"]] = {"ok": False, "value": 0.0, "error": "数据长度不足"}
                    continue
                fake_resp = [self.slave_id, FC_READ_HOLDING, reg_count * 2] + list(p_data)
                parsed = parse_read_response(fake_resp, p)
                result[p["name"]] = {"ok": True, "value": parsed["eng_value"], "error": ""}

        return result

    def write_param(self, param: dict, eng_value: float) -> dict:
        """写入单个参数（功能码 06）。含断线检测、超时重试、echo 校验。"""
        if self.connection_state != "connected":
            return {"ok": False, "error": "串口未连接", "retried": 0}

        decimals = int(param.get("decimals", 0))
        scale = 10 ** decimals
        raw_value = round(float(eng_value) * scale)

        last_error = ""
        retried = 0

        for attempt in range(CONFIG["max_retries"] + 1):
            frame = build_write_frame(self.slave_id, param["address"], raw_value)
            result = self._transact_once(frame, None, is_write=True)

            if result["type"] == "ok":
                # 写响应 = echo，校验是否与请求一致
                if result["resp"] != frame:
                    last_error = "写响应与请求不匹配"
                    if attempt < CONFIG["max_retries"]:
                        retried += 1
                        continue
                    return {"ok": False, "error": last_error, "retried": retried}
                return {"ok": True, "frame": frame, "response": result["resp"], "retried": retried}

            if result["type"] == "timeout":
                last_error = "从站无响应（超时）"
                self._log("rx", "TIMEOUT", f"等待 {CONFIG['timeout_ms']}ms 无响应")
                if attempt < CONFIG["max_retries"]:
                    retried += 1
                    continue
                return {"ok": False, "error": last_error, "retried": retried}

            if result["type"] == "crc_error":
                last_error = "回包 CRC 错误"
                if attempt < CONFIG["max_retries"]:
                    retried += 1
                    continue
                return {"ok": False, "error": last_error, "retried": retried}

        return {"ok": False, "error": last_error or "未知错误", "retried": retried}
