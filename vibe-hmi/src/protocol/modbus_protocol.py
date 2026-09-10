"""
Modbus RTU 协议层

迁移自原型 assets/hmi/js/components/modbusProtocol.js。
把参数表（address/type/access）翻译成真实 Modbus RTU 报文（含 CRC16）。

这是"内部逻辑"——报文格式固定，不让用户碰。
纯 Python，不依赖 PySide6/Qt，可独立 pytest。

PySide6 阶段：把 simulate_read_response / transact_once 替换为
pymodbus 的 client.read_holding_registers / write_register，接口不变。
"""
import math
import struct
import random
import time

# Modbus 功能码
FC_READ_HOLDING = 0x03
FC_WRITE_SINGLE = 0x06

# 协议层配置
CONFIG = {
    # 超时阈值：低波特率设备（2400/4800）单包 8~20 字节往返可达 200~300ms，
    # 国网协议 FC=0x66 实测约 215ms，故提到 300ms 以覆盖低速场景。
    "timeout_ms": 380,       # 超时阈值
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


# 国网协议（表计通信标识）
# 读请求帧固定格式：<slave> 66 03 01 20 00 <CRC_LO> <CRC_HI>（8 字节）
# 功能码 0x66 是非标准 Modbus FC，用于国网协议自定义读命令。
GW_FC = 0x66
GW_READ_PAYLOAD = [0x03, 0x01, 0x20, 0x00]  # 固定的寄存器地址/数量字段
GW_READ_HEADER_LEN = 5  # 响应中 slave(1) + FC(1) + byteCount(1) + 头(5) 共 8 字节头


def build_gw_read_frame(slave_id: int) -> list[int]:
    """生成国网协议「读取表计通信标识」请求帧（FC=0x66）。

    例：slave=2 → [0x02, 0x66, 0x03, 0x01, 0x20, 0x00, 0x41, 0xB5]
        slave=1 → [0x01, 0x66, 0x03, 0x01, 0x20, 0x00, 0x41, 0x86]
    """
    frame = [slave_id & 0xFF, GW_FC] + GW_READ_PAYLOAD
    return append_crc(frame)


def parse_gw_read_response(resp: list[int]) -> dict | None:
    """解析国网协议读响应。

    响应结构（20 字节）：
        [0]    slave
        [1]    FC (0x66)
        [2]    byte count (0x0F = 15)
        [3..7] 头(5 字节，协议固定，目前不使用)
        [8]    通讯地址
        [9]    波特率代码（0=2400 / 1=4800 / 2=9600 / 3=19200）
        [10]   奇偶校验代码（0=无 / 1=奇 / 2=偶）
        [11..12] 年（LE 2 字节，如 0x07EA = 2026）
        [13]   月
        [14]   日
        [15]   时
        [16]   分
        [17]   秒
        [18..19] CRC（LE 2 字节）

    校验失败或长度不足返回 None。
    """
    # 至少需要 1+1+1+5+1+1+1+2+1+1+1+1+1+2 = 20 字节
    if len(resp) < 8 + 1 + 1 + 1 + 2 + 1 + 1 + 1 + 1 + 1 + 2:
        return None
    if resp[1] != GW_FC:
        return None
    if not verify_crc(resp):
        return None

    addr = resp[8]
    baud_code = resp[9]
    parity_code = resp[10]
    year = (resp[12] << 8) | resp[11]  # LE：字节序列 EA 07 → 0x07EA = 2026
    month = resp[13]
    day = resp[14]
    hour = resp[15]
    minute = resp[16]
    second = resp[17]

    return {
        "addr": addr,
        "baud_code": baud_code,
        "parity_code": parity_code,
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
        "second": second,
    }



# 国网协议（表计通信标识）写命令
# 帧结构：<slave> 66 <byteCount> <5字节头> <数据> <CRC_LO> <CRC_HI>
# 5 字节头格式：02 20 <sub_id> <fmt> <len>
#   sub_id: 01=通信地址 / 02=波特率 / 03=奇偶校验位 / 04=日期时间
#   fmt:    20 = 单字节写, 40 = 多字节写
#   len:    01 = 1 字节数据, 07 = 7 字节数据（2 字节年 + 5 字节 MDHMS）
# 单字节写：byteCount=0x06（5 头 + 1 数据），总帧 12 字节
# 多字节写：byteCount=0x0C（5 头 + 7 数据），总帧 17 字节
GW_WRITE_HEADER_ADDR   = [0x02, 0x20, 0x01, 0x20, 0x01]  # 通信地址 (sub_id=0x01)
GW_WRITE_HEADER_BAUD   = [0x02, 0x20, 0x02, 0x20, 0x01]  # 波特率   (sub_id=0x02)
GW_WRITE_HEADER_PARITY = [0x02, 0x20, 0x03, 0x20, 0x01]  # 奇偶校验位 (sub_id=0x03)
GW_WRITE_HEADER_DT     = [0x02, 0x20, 0x04, 0x40, 0x07]  # 日期时间 (sub_id=0x04)

# 写命令子 ID（用于响应解析中识别）
GW_WRITE_SUB_ADDR = 0x01
GW_WRITE_SUB_BAUD = 0x02
GW_WRITE_SUB_PARITY = 0x03
GW_WRITE_SUB_DT = 0x04


def _build_gw_write_frame(slave_id: int, header: list[int], data: list[int]) -> list[int]:
    """通用国网写帧构建：<slave> 66 <byteCount> <header> <data> <CRC>

    byteCount = 5 字节头 + 数据字节数。
    """
    payload = list(header) + list(data)
    byte_count = len(payload) & 0xFF
    frame = [slave_id & 0xFF, GW_FC, byte_count] + payload
    return append_crc(frame)


def build_gw_write_baud_frame(slave_id: int, baud_code: int) -> list[int]:
    """国网协议：写波特率。

    例：slave=2, baud=9600(2) → 02 66 06 02 20 02 20 01 02 <CRC>
    """
    if baud_code not in (0, 1, 2, 3):
        raise ValueError(f"baud_code 必须是 0/1/2/3，得到 {baud_code}")
    return _build_gw_write_frame(slave_id, GW_WRITE_HEADER_BAUD, [baud_code & 0xFF])


def build_gw_write_parity_frame(slave_id: int, parity_code: int) -> list[int]:
    """国网协议：写奇偶校验位。

    例：slave=2, parity=0(无校验) → 02 66 06 02 20 03 20 01 00 <CRC>
    """
    if parity_code not in (0, 1, 2):
        raise ValueError(f"parity_code 必须是 0/1/2，得到 {parity_code}")
    return _build_gw_write_frame(slave_id, GW_WRITE_HEADER_PARITY, [parity_code & 0xFF])


def build_gw_write_datetime_frame(slave_id: int, year: int, month: int,
                                  day: int, hour: int, minute: int, second: int) -> list[int]:
    """国网协议：写日期时间。

    数据格式（7 字节）：<year_LO> <year_HI> <month> <day> <hour> <minute> <second>
    年份按小端 2 字节编码（如 2026 → 0x07EA → 字节序列 EA 07）。

    例：slave=2, 2021-07-29 15:33:58 →
        02 66 0C 02 20 04 40 07 E5 07 07 1D 0F 21 3A 78 76
    """
    if not (2000 <= year <= 2099):
        raise ValueError(f"年份超出范围 (2000~2099)：{year}")
    if not (1 <= month <= 12):
        raise ValueError(f"月份非法：{month}")
    if not (1 <= day <= 31):
        raise ValueError(f"日期非法：{day}")
    if not (0 <= hour <= 23):
        raise ValueError(f"小时非法：{hour}")
    if not (0 <= minute <= 59):
        raise ValueError(f"分钟非法：{minute}")
    if not (0 <= second <= 59):
        raise ValueError(f"秒非法：{second}")

    year_lo = year & 0xFF
    year_hi = (year >> 8) & 0xFF
    data = [year_lo, year_hi, month, day, hour, minute, second]
    return _build_gw_write_frame(slave_id, GW_WRITE_HEADER_DT, data)


def build_gw_write_addr_frame(slave_id: int, addr: int) -> list[int]:
    """国网协议：写通信地址。

    例：slave=2, addr=1 → 02 66 06 02 20 01 20 01 01 B3 D1
    """
    if not (1 <= addr <= 247):
        raise ValueError(f"通信地址必须 1~247，得到 {addr}")
    return _build_gw_write_frame(slave_id, GW_WRITE_HEADER_ADDR, [addr & 0xFF])


def parse_gw_write_response(resp: list[int], request: list[int]) -> dict | None:
    """解析国网协议写响应。

    响应按"回显请求"约定：设备收到合法写命令后原样回传（便于上层按 CRC + 字节数判定）。
    异常时设备可能返回 0x86（FC|0x80）等异常帧，本函数对异常帧不特别处理，
    只在长度/CRC/FC 三项通过时返回 dict。

    返回：
        ok: True 表示回包 CRC 通过且 FC 正确
        sub_id: 写入的子项（01=地址/02=波特率/03=校验/04=时间），从请求头提取
        echo: 回包原始字节列表
    失败返回 None。
    """
    # 最少：slave(1) + FC(1) + byteCount(1) + 0 数据 + CRC(2) = 5 字节
    if len(resp) < 5:
        return None
    if resp[1] != GW_FC:
        return None
    if not verify_crc(resp):
        return None

    # 从请求头识别写入子项（请求第 5 字节 = header[2] = sub_id）
    # 请求布局：<slave> 66 <byteCount> 02 20 <sub_id> ...
    sub_id = request[5] if len(request) > 5 else 0

    return {
        "ok": True,
        "sub_id": sub_id,
        "echo": resp,
    }


# 国网协议（阈值设置）读取
# 请求帧：<slave> 66 09 01 22 06 22 07 22 08 22 09 <CRC_LO> <CRC_HI>（14 字节）
#   - byteCount=9：1 字节前缀(0x01) + 4 个 DI（每个 2 字节）
# 响应帧：<slave> 66 21 81 <组0> <组1> <组2> <组3> <CRC_LO> <CRC_HI>（38 字节）
#   - byteCount=33：1 字节前缀(0x81) + 4 个数据组（每组 8 字节）
#   - 每组布局：<DI_LO DI_HI> <fmt_LO fmt_HI> <float32_BE×4>
#   - 26 04 表示后续 4 字节是 float32 数据
# 国网协议（温度压力密度数据）读取
# 请求帧：<slave> 66 09 01 22 02 22 03 22 04 22 05 <CRC_LO> <CRC_HI>（14 字节）
#   - byteCount=9：1 字节前缀(0x01) + 4 个 DI（每个 2 字节）
# 响应帧：<slave> 66 21 81 <组0> <组1> <组2> <组3> <CRC_LO> <CRC_HI>（38 字节）
#   - byteCount=33：1 字节前缀(0x81) + 4 个数据组（每组 8 字节）
#   - 每组布局：<DI_LO DI_HI> <fmt_LO fmt_HI> <float32_LE×4>
#   - 26 04 表示后续 4 字节是 float32 数据
GW_REALTIME_DI_DENSITY   = 0x2202  # 密度值
GW_REALTIME_DI_TEMP      = 0x2203  # 温度值
GW_REALTIME_DI_PRESSURE  = 0x2204  # 相对压力
GW_REALTIME_DI_WATER     = 0x2205  # 微水

# 4 个实时数据 DI（顺序固定）
GW_REALTIME_DIS = [
    GW_REALTIME_DI_DENSITY,
    GW_REALTIME_DI_TEMP,
    GW_REALTIME_DI_PRESSURE,
    GW_REALTIME_DI_WATER,
]


def build_gw_realtime_read_frame(slave_id: int) -> list[int]:
    """生成国网协议「读取温度压力密度数据」请求帧（FC=0x66）。

    帧结构：<slave> 66 09 01 22 02 22 03 22 04 22 05 <CRC_LO> <CRC_HI>
    长度固定 14 字节；byteCount=9（1 字节前缀 + 4 个 2 字节 DI）。

    例：slave=2 → [02, 66, 09, 01, 22, 02, 22, 03,
                   22, 04, 22, 05, D1, 6A]
    """
    payload = [0x01]  # 读请求前缀
    for di in GW_REALTIME_DIS:
        payload.append((di >> 8) & 0xFF)  # DI 高字节
        payload.append(di & 0xFF)         # DI 低字节
    byte_count = len(payload) & 0xFF
    frame = [slave_id & 0xFF, GW_FC, byte_count] + payload
    return append_crc(frame)


def parse_gw_realtime_read_response(resp: list[int]) -> dict | None:
    """解析国网协议「读取温度压力密度数据」响应。

    响应结构（38 字节）：
        [0]      slave
        [1]      FC (0x66)
        [2]      byte count (0x21 = 33)
        [3]      prefix (0x81)
        [4..35]  数据区（32 字节 = 4 组 × 8 字节），每组：
                  [DI_LO DI_HI fmt_LO fmt_HI float32_LE×4]
        [36..37] CRC（LE 2 字节）

    数据为 IEEE754 float32 小端（低字节在前）：
        例：字节序列 "40 D4 06 BB" → 0xBB06D440 → float32 密度值

    设备用全 0xFF（4 字节 = NaN）表示该字段"无效/未采集"，
    解析时该 DI 的值设为 None，由 UI 显示 `------`。

    返回 {DI: float_value | None} 字典；
    CRC / FC / 长度校验失败返回 None。
    """
    # 最少需要：1(slave) + 1(FC) + 1(byteCount) + 1(prefix) + 8*4 + 2(CRC) = 38
    if len(resp) < 4 + 8 * 4 + 2:
        return None
    if resp[1] != GW_FC:
        return None
    if not verify_crc(resp):
        return None

    # 数据区：去掉 slave/FC/byteCount/prefix 头和 CRC 尾
    payload = resp[4:-2]
    if len(payload) < 8 * 4:
        return None

    values: dict[int, float | None] = {}
    # 每组 8 字节：DI(2) + fmt(2) + float32 LE(4)
    for i in range(len(payload) // 8):
        offset = i * 8
        di = (payload[offset] << 8) | payload[offset + 1]
        data = payload[offset + 4:offset + 8]
        # 全 0xFF = NaN（设备"无效/未采集"标记），值设为 None
        if data == [0xFF, 0xFF, 0xFF, 0xFF]:
            values[di] = None
            continue
        try:
            value = struct.unpack("<f", bytes(data))[0]
        except Exception:
            values[di] = None
            continue
        if math.isnan(value) or math.isinf(value):
            values[di] = None
            continue
        values[di] = value

    return values


GW_THRESHOLD_DI_ALARM     = 0x2206  # 报警节点阈值
GW_THRESHOLD_DI_LOCK1     = 0x2207  # 闭锁1阈值
GW_THRESHOLD_DI_LOCK2     = 0x2208  # 闭锁2阈值
GW_THRESHOLD_DI_OVERPRESS = 0x2209  # 超压节点阈值

# 4 个阈值 DI（顺序固定，DI 高字节在前便于构造帧）
GW_THRESHOLD_DIS = [
    GW_THRESHOLD_DI_ALARM,
    GW_THRESHOLD_DI_LOCK1,
    GW_THRESHOLD_DI_LOCK2,
    GW_THRESHOLD_DI_OVERPRESS,
]


def build_gw_threshold_read_frame(slave_id: int) -> list[int]:
    """生成国网协议「读取阈值」请求帧（FC=0x66）。

    帧结构：<slave> 66 09 01 22 06 22 07 22 08 22 09 <CRC_LO> <CRC_HI>
    长度固定 14 字节；byteCount=9（1 字节前缀 + 4 个 2 字节 DI）。

    例：slave=2 → [02, 66, 09, 01, 22, 06, 22, 07,
                   22, 08, 22, 09, A5, 6C]
    """
    payload = [0x01]  # 读请求前缀
    for di in GW_THRESHOLD_DIS:
        payload.append((di >> 8) & 0xFF)  # DI 高字节
        payload.append(di & 0xFF)         # DI 低字节
    byte_count = len(payload) & 0xFF
    frame = [slave_id & 0xFF, GW_FC, byte_count] + payload
    return append_crc(frame)


def build_gw_threshold_write_frame(slave_id: int, di: int,
                                   data_bytes: list[int]) -> list[int]:
    """生成国网协议「写入单个阈值」请求帧（FC=0x66）。

    帧结构：<slave> 66 09 02 <DI_HI> <DI_LO> 26 04 <data×4> <CRC_LO> <CRC_HI>
    长度固定 17 字节；byteCount=9（1 字节前缀 + 2 字节 DI + 2 字节 fmt + 4 字节数据）。

    参数：
        slave_id: 从机地址（1~247）
        di: DI 标识（0x2206=报警 / 0x2207=闭锁1 / 0x2208=闭锁2 / 0x2209=超压）
        data_bytes: 4 字节数据（float32 小端，或全 FFFFFFFF 表示无效/未配置）

    例：slave=1, di=0x2206, data=[0x9A,0x99,0x19,0x3F]（0.6 的 float32 LE）→
        01 66 09 02 22 06 26 04 9A 99 19 3F 16 77
    """
    if not (1 <= slave_id <= 247):
        raise ValueError(f"从机地址必须 1~247，得到 {slave_id}")
    if len(data_bytes) != 4:
        raise ValueError(f"数据必须为 4 字节，得到 {len(data_bytes)} 字节")
    payload = [
        0x02,                       # 写命令前缀
        (di >> 8) & 0xFF,          # DI 高字节
        di & 0xFF,                 # DI 低字节
        0x26, 0x04,                # 格式标识（4 字节 float32）
    ] + list(data_bytes)
    byte_count = len(payload) & 0xFF  # = 0x09
    frame = [slave_id & 0xFF, GW_FC, byte_count] + payload
    return append_crc(frame)


def parse_gw_threshold_write_response(resp: list[int], request: list[int]) -> dict | None:
    """解析国网协议「阈值写入」响应。

    响应按"回显请求"约定：设备收到合法写命令后原样回传，
    上层按 CRC + byteCount 判定成功与否。

    返回：
        ok: True 表示回包 CRC 通过且 FC 正确
        echo: 回包原始字节列表
    失败返回 None。
    """
    # 最少：slave(1) + FC(1) + byteCount(1) + data + CRC(2) = 至少 5 字节
    if len(resp) < 5:
        return None
    if resp[1] != GW_FC:
        return None
    if not verify_crc(resp):
        return None
    return {
        "ok": True,
        "echo": resp,
    }


def parse_gw_threshold_read_response(resp: list[int]) -> dict | None:
    """解析国网协议「读取阈值」响应。

    响应结构（38 字节）：
        [0]      slave
        [1]      FC (0x66)
        [2]      byte count (0x21 = 33)
        [3]      prefix (0x81)
        [4..35]  数据区（32 字节 = 4 组 × 8 字节），每组：
                  [DI_LO DI_HI fmt_LO fmt_HI float32_LE×4]
        [36..37] CRC（LE 2 字节）

    数据为 IEEE754 float32 小端（低字节在前）：
        例：字节序列 "14 AE 07 3F" → 0x3F07AE14 → 0.7800

    设备用全 0xFF（4 字节 = NaN）表示该阈值"无效/未配置"，解析时直接跳过，
    返回字典中不会出现该 DI，由 UI 显示 `------`。

    返回 {DI: float_value} 字典（仅含有效数值的 DI）；
    CRC / FC / 长度校验失败返回 None。
    """
    # 最少需要：1(slave) + 1(FC) + 1(byteCount) + 1(prefix) + 8*4 + 2(CRC) = 38
    if len(resp) < 4 + 8 * 4 + 2:
        return None
    if resp[1] != GW_FC:
        return None
    if not verify_crc(resp):
        return None

    # 数据区：去掉 slave/FC/byteCount/prefix 头和 CRC 尾
    payload = resp[4:-2]
    if len(payload) < 8 * 4:
        return None

    values: dict[int, float] = {}
    # 每组 8 字节：DI(2) + fmt(2) + float32 LE(4)
    for i in range(len(payload) // 8):
        offset = i * 8
        di = (payload[offset] << 8) | payload[offset + 1]
        # fmt = (payload[offset+2] << 8) | payload[offset+3]  # 协议固定 26 04，暂未使用
        data = payload[offset + 4:offset + 8]
        # 全 0xFF = NaN（设备"无效/未配置"标记），跳过不入字典
        if data == [0xFF, 0xFF, 0xFF, 0xFF]:
            continue
        try:
            value = struct.unpack("<f", bytes(data))[0]
        except Exception:
            continue
        # 防御性：struct.unpack 也可能给出 NaN（异常位模式），同样视为无效
        if math.isnan(value) or math.isinf(value):
            continue
        values[di] = value

    return values


# 国网协议（传感器状态）读取
# 请求帧：<slave> 66 03 01 22 01 <CRC_LO> <CRC_HI>（8 字节）
#   - byteCount=3：1 字节前缀(0x01) + 1 个 DI(2 字节)
# 响应帧：<slave> 66 07 81 22 01 04 02 <status_LO> <status_HI> <CRC_LO> <CRC_HI>（12 字节）
#   - byteCount=7：1 字节前缀(0x81) + 2 字节 DI + 2 字节长度(04 02) + 2 字节状态数据
#   - 状态数据按小端 uint16 解析，再按位反转后提取 Bit0~Bit9
GW_SENSOR_STATUS_DI = 0x2201  # 传感器状态 DI 标识


def build_gw_sensor_status_read_frame(slave_id: int) -> list[int]:
    """生成国网协议「读取传感器状态」请求帧（FC=0x66）。

    帧结构：<slave> 66 03 01 22 01 <CRC_LO> <CRC_HI>
    长度固定 8 字节；byteCount=3（1 字节前缀 + 1 个 2 字节 DI）。

    例：slave=2 → [02, 66, 03, 01, 22, 01, 81, 15]
    """
    payload = [
        0x01,                               # 读请求前缀
        (GW_SENSOR_STATUS_DI >> 8) & 0xFF,  # DI 高字节 (0x22)
        GW_SENSOR_STATUS_DI & 0xFF,         # DI 低字节 (0x01)
    ]
    byte_count = len(payload) & 0xFF  # = 0x03
    frame = [slave_id & 0xFF, GW_FC, byte_count] + payload
    return append_crc(frame)


def parse_gw_sensor_status_response(resp: list[int]) -> dict | None:
    """解析国网协议「读取传感器状态」响应。

    响应结构（12 字节）：
        [0]      slave
        [1]      FC (0x66)
        [2]      byte count (0x07 = 7)
        [3]      prefix (0x81)
        [4..5]   DI (0x2201)
        [6..7]   长度标识 (0x04 0x02)
        [8..9]   状态数据（小端 uint16）
        [10..11] CRC（LE 2 字节）

    状态数据解析步骤：
        1. 小端 uint16 解析（如字节 C2 01 → 0x01C2）
        2. 转 16 位二进制字符串
        3. 反转字符串（bit reversal）
        4. 提取 Bit0~Bit9（0=正常，1=故障/动作）

    返回字典：
        sensor_status: bool (Bit0 - 传感器整体状态)
        leak_alarm: bool (Bit1 - 泄漏报警)
        liquefaction_alarm: bool (Bit2 - 液化报警)
        lock2_wiring_fault: bool (Bit3 - 闭锁2节点接线故障)
        lock1_wiring_fault: bool (Bit4 - 闭锁1节点接线故障)
        alarm_wiring_fault: bool (Bit5 - 报警节点接线故障)
        lock2_action: bool (Bit6 - 闭锁2信号节点动作)
        lock1_action: bool (Bit7 - 闭锁1信号节点动作)
        alarm_action: bool (Bit8 - 报警信号节点动作)
        overpressure_alarm: bool (Bit9 - 超压报警)

    CRC / FC / 长度校验失败返回 None。
    """
    # 最少需要：1(slave) + 1(FC) + 1(byteCount) + 1(prefix) + 2(DI) + 2(len) + 2(status) + 2(CRC) = 12
    if len(resp) < 12:
        return None
    if resp[1] != GW_FC:
        return None
    if not verify_crc(resp):
        return None

    # 提取状态数据（小端 uint16）
    status_raw = (resp[9] << 8) | resp[8]  # 小端：低字节在前

    # 转 16 位二进制字符串并反转（bit reversal）
    # 例：0x01C2 = "0000000111000010" → 反转 → "0100000111000000"
    # 反转后，字符串从左到右依次是 Bit0, Bit1, Bit2, ...
    bin_str = f"{status_raw:016b}"
    reversed_str = bin_str[::-1]

    # 按字符串位置提取各 bit（'0'=正常，'1'=故障/动作）
    # reversed_str[0] = Bit0, reversed_str[1] = Bit1, ...
    return {
        "sensor_status":        reversed_str[0] == '1',  # Bit0
        "leak_alarm":           reversed_str[1] == '1',  # Bit1
        "liquefaction_alarm":   reversed_str[2] == '1',  # Bit2
        "lock2_wiring_fault":   reversed_str[3] == '1',  # Bit3
        "lock1_wiring_fault":   reversed_str[4] == '1',  # Bit4
        "alarm_wiring_fault":   reversed_str[5] == '1',  # Bit5
        "lock2_action":         reversed_str[6] == '1',  # Bit6
        "lock1_action":         reversed_str[7] == '1',  # Bit7
        "alarm_action":         reversed_str[8] == '1',  # Bit8
        "overpressure_alarm":   reversed_str[9] == '1',  # Bit9
    }


def float32_to_bytes(value: float) -> list[int]:
    """float32 → 4 字节（IEEE754 Big-Endian，高字在前）"""
    return list(struct.pack(">f", value))


def bytes_to_float32(data: list[int]) -> float:
    """4 字节 → float32（IEEE754 Big-Endian）"""
    return struct.unpack(">f", bytes(data))[0]


def float32_to_bytes_le(value: float) -> list[int]:
    """float32 → 4 字节（IEEE754 Little-Endian，低字节在前）"""
    return list(struct.pack("<f", value))


def bytes_to_float32_le(data: list[int]) -> float:
    """4 字节 → float32（IEEE754 Little-Endian，低字节在前）"""
    return struct.unpack("<f", bytes(data))[0]


# 国网协议（设备基本信息标识）读取
# 请求帧：<slave> 66 07 01 21 01 21 02 21 03 <CRC_LO> <CRC_HI>（12 字节）
#   - byteCount=7：1 字节前缀(0x01) + 3 个 DI（每个 2 字节：21 01/21 02/21 03）
# 响应帧：<slave> 66 <byteCount> 81 <TLV×3> <CRC_LO> <CRC_HI>
#   - TLV 每项格式：<type=0x21> <id> <sub> <data_len> <data×data_len>
#     sub: 子项编号（协议内部用，解析时跳过）
#     data_len: 纯数据字节数
#     · 21 01 sub=0x05 data_len=0x10(16)：设备型号（ASCII，16 字节，不足补 0x00）
#     · 21 02 sub=0x04 data_len=0x06(6)：表计 ID（H）（十六进制字节序列，6 字节）
#     · 21 03 sub=0x20 data_len=0x01(1)：传感器类型标识（1 字节代码）
GW_DEV_INFO_DI_MODEL   = 0x2101  # 设备型号
GW_DEV_INFO_DI_MID_H   = 0x2102  # 表计 ID（H）
GW_DEV_INFO_DI_SENSOR  = 0x2103  # 传感器类型标识

# 传感器类型标识映射
GW_SENSOR_TYPE_MAP = {
    0x01: "SF6数字化密度表",
    0x02: "避雷器数字化泄漏电流",
    0x03: "变压器数字化油面温度表计",
    0x04: "变压器数字化绕组温度表计",
    0x05: "变压器数字化油位计",
    0x06: "变压器数字化气体继电器",
}

# 3 个设备信息 DI（顺序固定）
GW_DEV_INFO_DIS = [
    GW_DEV_INFO_DI_MODEL,
    GW_DEV_INFO_DI_MID_H,
    GW_DEV_INFO_DI_SENSOR,
]


def build_gw_dev_info_read_frame(slave_id: int) -> list[int]:
    """生成国网协议「读取设备基本信息标识」请求帧（FC=0x66）。

    帧结构：<slave> 66 07 01 21 01 21 02 21 03 <CRC_LO> <CRC_HI>
    长度固定 12 字节；byteCount=7（1 字节前缀 + 3 个 2 字节 DI）。

    例：slave=1 → 01 66 07 01 21 01 21 02 21 03 3B 9A
    """
    payload = [0x01]  # 读请求前缀
    for di in GW_DEV_INFO_DIS:
        payload.append((di >> 8) & 0xFF)  # DI 高字节
        payload.append(di & 0xFF)         # DI 低字节
    byte_count = len(payload) & 0xFF  # = 0x07
    frame = [slave_id & 0xFF, GW_FC, byte_count] + payload
    return append_crc(frame)


def parse_gw_dev_info_response(resp: list[int]) -> dict | None:
    """解析国网协议「读取设备基本信息标识」响应。

    响应结构（实测 41 字节）：
        [0]      slave
        [1]      FC (0x66)
        [2]      byte count
        [3]      prefix (0x81)
        [4..-3]  TLV 数据区，每项格式：
                  <type=0x21> <id> <sub> <data_len> <data×data_len>
        [-2..-1] CRC（LE 2 字节）

    实测 TLV 项（来自真实设备回包）：
        21 01 05 10 <16字节ASCII>  → 设备型号 "RDM\\0..."
        21 02 04 06 <6字节hex>     → 表计 ID（H）"C1C408200000"
        21 03 20 01 <1字节code>    → 传感器类型标识 0x01

    返回字典：
        model:       str  设备型号（ASCII，去尾部 0x00）
        meter_id_h:  str  表计 ID（H）大写 hex 字符串
        sensor_type: str  传感器类型名称
        sensor_type_code: int  传感器类型原始代码

    CRC / FC / 长度校验失败返回 None。
    """
    # 最少：1(slave) + 1(FC) + 1(byteCount) + 1(prefix) + TLV + 2(CRC)
    # TLV 每项最少 5 字节（type+id+sub+datalen+1byte data），3 项 = 15
    if len(resp) < 4 + 15 + 2:
        return None
    if resp[1] != GW_FC:
        return None
    if not verify_crc(resp):
        return None

    # 数据区：去掉 slave/FC/byteCount/prefix 头和 CRC 尾
    payload = resp[4:-2]

    # 解析 TLV：<type> <id> <sub> <data_len> <data×data_len>
    result: dict = {}
    offset = 0
    while offset + 4 <= len(payload):
        tlv_type = payload[offset]
        tlv_id = payload[offset + 1]
        # payload[offset+2] = sub（子项编号，跳过）
        data_len = payload[offset + 3]  # 第 4 字节 = 纯数据字节数
        if offset + 4 + data_len > len(payload):
            break  # 数据不足，停止解析
        data = payload[offset + 4:offset + 4 + data_len]
        di = (tlv_type << 8) | tlv_id

        if di == GW_DEV_INFO_DI_MODEL:
            # ASCII 字符串，去掉尾部 0x00 填充
            model_bytes = bytes(b for b in data if b != 0x00)
            result["model"] = model_bytes.decode("ascii", errors="replace")
        elif di == GW_DEV_INFO_DI_MID_H:
            # 十六进制字节序列 → 大写 hex 字符串
            result["meter_id_h"] = "".join(f"{b:02X}" for b in data)
        elif di == GW_DEV_INFO_DI_SENSOR:
            code = data[0] if data else 0
            result["sensor_type_code"] = code
            result["sensor_type"] = GW_SENSOR_TYPE_MAP.get(code, f"未知类型(0x{code:02X})")

        offset += 4 + data_len

    # 校验必要字段
    if "model" not in result or "meter_id_h" not in result or "sensor_type" not in result:
        return None

    return result


# 国网协议（设备基本信息标识）写入
# 写表计ID（H）：
#   <slave> 10 07 D0 00 03 06 <6字节meter_id> <CRC_LO CRC_HI>
#   数据长度 0x06 = 6 字节（表计ID 6字节）
# 写设备型号：
#   <slave> 10 07 DC 00 08 10 <16字节ASCII> <CRC_LO CRC_HI>
#   数据长度 0x10 = 16 字节（设备型号 ASCII，不足补 0x00）


def build_gw_write_meter_id_frame(slave_id: int, meter_id_h: str) -> list[int]:
    """生成国网协议「写入表计ID（H）」请求帧。

    帧结构：<slave> 10 07 D0 00 03 06 <6字节meter_id> <CRC_LO CRC_HI>

    参数：
        slave_id:  从机地址（1~247）
        meter_id_h: 表计ID（H）大写 hex 字符串，如 "C1C4082927C1"（12 个字符 = 6 字节）

    例：slave=1, meter_id="C1C4082927C1" →
        01 10 07 D0 00 03 06 C1 C4 08 29 27 C1 <CRC>
    """
    if not (1 <= slave_id <= 247):
        raise ValueError(f"从机地址必须 1~247，得到 {slave_id}")
    # meter_id_h 应为 12 个 hex 字符（6 字节）
    clean = meter_id_h.strip().upper()
    if len(clean) != 12:
        raise ValueError(f"表计ID（H）必须为 12 个 hex 字符（6 字节），得到 {len(clean)} 个字符")
    try:
        meter_bytes = [int(clean[i:i + 2], 16) for i in range(0, 12, 2)]
    except ValueError:
        raise ValueError(f"表计ID（H）包含非法 hex 字符：{clean}")

    # 帧结构：<slave> 10 07 D0 00 03 06 <data×6>
    frame = [
        slave_id & 0xFF,
        0x10, 0x07,           # 写命令标识
        0xD0, 0x00,           # 寄存器地址
        0x03, 0x06,           # 寄存器数量(3) / 字节数(6)
    ] + meter_bytes
    return append_crc(frame)


def parse_gw_write_meter_id_response(resp: list[int]) -> dict | None:
    """解析「写入表计ID（H）」响应。

    响应按"回显请求"约定：设备收到合法写命令后原样回传，
    上层按 CRC + FC 判定成功与否。

    返回：
        ok: True 表示回包 CRC 通过
        echo: 回包原始字节列表
    失败返回 None。
    """
    if len(resp) < 5:
        return None
    # 回包第 1 字节应为 0x10（与请求一致）
    if resp[1] != 0x10:
        return None
    if not verify_crc(resp):
        return None
    return {"ok": True, "echo": resp}


def build_gw_write_device_model_frame(slave_id: int, model: str) -> list[int]:
    """生成国网协议「写入设备型号」请求帧。

    帧结构：<slave> 10 07 DC 00 08 10 <16字节ASCII> <CRC_LO CRC_HI>

    参数：
        slave_id: 从机地址（1~247）
        model:    设备型号字符串，转 ASCII 后补 0x00 至 16 字节

    设备型号编码：每个字符取 ASCII 码值，不足 16 字节用 0x00 补齐。
    例：slave=1, model="R1.5G 1.1.52601"（16 字符）→
        01 10 07 DC 00 08 10 52 31 2E 35 47 20 31 2E 31 2E 35 32 36 30 31 00 <CRC>
    """
    if not (1 <= slave_id <= 247):
        raise ValueError(f"从机地址必须 1~247，得到 {slave_id}")

    # 设备型号 → 16 字节 ASCII（不足补 0x00）
    model_bytes = model.encode("ascii", errors="replace")[:16]
    # 补零到 16 字节
    model_data = list(model_bytes) + [0x00] * (16 - len(model_bytes))

    # 帧结构：<slave> 10 07 DC 00 08 10 <data×16>
    frame = [
        slave_id & 0xFF,
        0x10, 0x07,           # 写命令标识
        0xDC, 0x00,           # 寄存器地址
        0x08, 0x10,           # 寄存器数量(8) / 字节数(16)
    ] + model_data
    return append_crc(frame)


def parse_gw_write_device_model_response(resp: list[int]) -> dict | None:
    """解析「写入设备型号」响应。

    响应按"回显请求"约定：设备收到合法写命令后原样回传，
    上层按 CRC + FC 判定成功与否。

    返回：
        ok: True 表示回包 CRC 通过
        echo: 回包原始字节列表
    失败返回 None。
    """
    if len(resp) < 5:
        return None
    if resp[1] != 0x10:
        return None
    if not verify_crc(resp):
        return None
    return {"ok": True, "echo": resp}


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

    def _is_read_response(self, resp: list[int], reg_count: int) -> bool:
        """校验 resp 是否为合法的 Modbus 读响应帧（功能码 03）。

        正常响应格式：[slave][FC=0x03][byte_count=N][N字节数据][CRC低][CRC高]
        其中 byte_count 应等于 reg_count × 2。

        用于识别并拒绝以下非响应帧（CRC 可能巧合通过）：
        - 回显的请求帧（串口/设备 echo）：[slave][0x03][addrH][addrL][regH][regL][CRC]
          其第3字节是地址高位而非字节数，长度固定 8，且 byte_count ≠ reg_count×2
        - 异常响应帧：[slave][0x83][exception][CRC]
        - 长度不足的残帧
        """
        # 异常响应帧（功能码最高位为1）：不作为正常读响应，交给上层处理异常
        if len(resp) >= 2 and (resp[1] & 0x80):
            return False
        # 必须至少有 slave + FC + byte_count + CRC（5字节）
        if len(resp) < 5:
            return False
        # 功能码必须是 0x03（读保持寄存器）
        if resp[1] != FC_READ_HOLDING:
            return False
        # 第3字节（byte_count）必须等于 reg_count × 2
        expected_byte_count = reg_count * 2
        if resp[2] != expected_byte_count:
            return False
        # 数据区长度必须够（去掉 slave/FC/byteCount/CRC2 后应 ≥ byte_count）
        if len(resp) - 5 < expected_byte_count:
            return False
        return True

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
                        self._serial_manager.tx_failures += 1
                    if attempt < CONFIG["max_retries"]:
                        retried += 1
                        continue
                    return {"ok": False, "error": last_error, "retried": retried}

                # 响应格式校验：拒绝回显帧（串口echo）/异常响应/残帧
                # CRC 通过不代表是合法响应帧（请求帧的CRC也可能巧合通过）
                if not self._is_read_response(result["resp"], reg_count):
                    last_error = "非响应帧（可能是回显/异常响应）"
                    self._log("rx", "WARN", f"丢弃非响应帧：{last_error}")
                    # 计入通信统计（异常响应算请求失败）
                    if self._serial_manager:
                        self._serial_manager.tx_failures += 1
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

            # 响应格式校验：拒绝回显帧（串口echo）/异常响应/残帧
            if not self._is_read_response(resp, total_regs):
                self._log("rx", "WARN", "丢弃非响应帧（可能是回显/异常响应）")
                # 计入通信统计（异常响应算请求失败）
                if self._serial_manager:
                    self._serial_manager.tx_failures += 1
                for p in group:
                    result[p["name"]] = {"ok": False, "value": 0.0, "error": "非响应帧"}
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
