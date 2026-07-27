"""
AI 工具层

4 个只读工具的 JSON Schema + handler，供 LLM function calling 使用。
handler 调协议层 / store 获取真实数据。
"""
import json

from ..store import store
from ..protocol.modbus_protocol import ModbusProtocol
from ..serial.serial_manager import serial_manager


# ===== 工具 JSON Schema（OpenAI function calling 格式）=====

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_sensor",
            "description": "读取指定采样点的实时值、单位和状态。支持中文点位名（如温度、压力）或参数名（如 temperature）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "point": {"type": "string", "description": "采样点名称，如 温度、压力、密度"},
                },
                "required": ["point"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alarms",
            "description": "查询报警记录，可按级别和确认状态过滤。",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "string", "enum": ["预警", "一般", "提示"], "description": "报警级别（可选）"},
                    "unacknowledged": {"type": "boolean", "description": "是否只查未确认报警（可选）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trend",
            "description": "查询指定采样点的最近趋势数据（最近若干个采样点）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "point": {"type": "string", "description": "采样点名称"},
                },
                "required": ["point"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_all_sensors",
            "description": "一次性读取所有采样参数的实时值。当用户要求读取全部参数、所有传感器或多个点位时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_device_status",
            "description": "查询所有设备的在线/离线状态和基本信息。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


def _find_param_by_display(point: str) -> dict | None:
    """按 display 名或 name 模糊查找采样参数"""
    params = store.sample_params()
    # 精确匹配 display
    for p in params:
        if p.get("display", "") == point:
            return p
    # 精确匹配 name
    for p in params:
        if p.get("name", "") == point:
            return p
    # 模糊匹配
    for p in params:
        if point in p.get("display", "") or point in p.get("name", ""):
            return p
    return None


def _make_protocol() -> ModbusProtocol:
    """创建协议层实例（用当前设备的 slave_id）"""
    proto = ModbusProtocol(slave_id=store.get_slave_id(), connection_state=store.connection_state)
    proto.set_serial_transport(serial_manager)
    return proto


def handle_read_sensor(args: dict) -> dict:
    """读取传感器实时值"""
    point = args.get("point", "")
    p = _find_param_by_display(point)
    if not p:
        return {"ok": False, "error": f"未找到采样点 '{point}'", "summary": f"未找到采样点 '{point}'"}

    proto = _make_protocol()
    result = proto.read_param(p)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error", "读取失败"),
                "summary": f"读取 {p.get('display', p['name'])} 失败：{result.get('error', '')}"}

    value = result["value"]
    unit = p.get("unit", "")
    decimals = int(p.get("decimals", 0))
    display = p.get("display", p["name"])
    summary = f"{display} = {value:.{decimals}f} {unit}"
    return {
        "ok": True,
        "data": {"point": display, "value": round(value, decimals), "unit": unit,
                 "range": f"{p.get('min', '?')} ~ {p.get('max', '?')}"},
        "summary": summary,
    }


def handle_read_all_sensors(args: dict) -> dict:
    """一次性读取所有采样参数"""
    params = store.sample_params()
    if not params:
        return {"ok": False, "error": "无采样参数", "summary": "当前设备无采样参数"}

    proto = _make_protocol()
    # 用批量读取（合并连续地址，效率高）
    result = proto.read_params_batch(params)

    lines = []
    data = []
    for name, info in result.items():
        p = next((x for x in params if x["name"] == name), None)
        if not p:
            continue
        display = p.get("display", name)
        unit = p.get("unit", "")
        decimals = int(p.get("decimals", 0))
        if info["ok"]:
            val = round(info["value"], decimals)
            lines.append(f"  {display} = {val:.{decimals}f} {unit}")
            data.append({"point": display, "value": val, "unit": unit})
        else:
            lines.append(f"  {display} = 读取失败（{info.get('error', '')}）")

    summary = f"共读取 {len(params)} 个参数：\n" + "\n".join(lines)
    return {"ok": True, "data": data, "summary": summary}


def handle_get_alarms(args: dict) -> dict:
    """查询报警记录"""
    level = args.get("level")
    unack_only = args.get("unacknowledged", False)

    alarms = store.alarms
    if level:
        alarms = [a for a in alarms if a.get("level") == level]
    if unack_only:
        alarms = [a for a in alarms if not a.get("acknowledged")]

    if not alarms:
        summary = "没有符合条件的报警记录"
    else:
        lines = [f"  {a['time']} [{a.get('level', '')}] {a['content']}" for a in alarms]
        summary = f"共 {len(alarms)} 条报警：\n" + "\n".join(lines)

    return {
        "ok": True,
        "data": [{"time": a["time"], "content": a["content"],
                  "terminal": a.get("terminal", ""), "level": a.get("level", ""),
                  "status": "已确认" if a.get("acknowledged") else "未确认"}
                 for a in alarms],
        "summary": summary,
    }


def handle_get_trend(args: dict) -> dict:
    """查询趋势数据（从 SQLite 最近 12 个点）"""
    from ..history_db import query as db_query

    point = args.get("point", "")
    p = _find_param_by_display(point)
    if not p:
        return {"ok": False, "error": f"未找到采样点 '{point}'", "summary": f"未找到采样点 '{point}'"}

    rows = db_query(
        device_id=store.current_device_id,
        param_names=[p["name"]],
    )
    # 取最近 12 个点
    rows = rows[-12:] if len(rows) > 12 else rows

    if not rows:
        summary = f"暂无 {p.get('display', p['name'])} 的历史趋势数据"
    else:
        values = [r["value"] for r in rows]
        avg = sum(values) / len(values)
        peak = max(values)
        decimals = int(p.get("decimals", 0))
        display = p.get("display", p["name"])
        unit = p.get("unit", "")
        summary = (f"{display} 最近 {len(values)} 个点："
                   f"平均 {avg:.{decimals}f} {unit}，峰值 {peak:.{decimals}f} {unit}")

    return {
        "ok": True,
        "data": {"point": p.get("display", p["name"]),
                 "points": [{"timestamp": r["timestamp"], "value": r["value"]} for r in rows],
                 "avg": avg if rows else 0, "peak": peak if rows else 0},
        "summary": summary,
    }


def handle_get_device_status(args: dict) -> dict:
    """查询设备状态"""
    devices = store.devices
    connected = serial_manager.is_connected

    lines = []
    for d in devices:
        status = "在线" if connected else "离线"
        lines.append(f"  {d['name']}（slave {d.get('slave_id', 1)}）：{status}")

    summary = f"共 {len(devices)} 台设备：\n" + "\n".join(lines) if lines else "暂无设备"
    return {
        "ok": True,
        "data": [{"name": d["name"], "slave_id": d.get("slave_id", 1),
                  "status": "在线" if connected else "离线",
                  "desc": d.get("desc", "")} for d in devices],
        "summary": summary,
    }


# ===== 工具分发 =====

HANDLERS = {
    "read_sensor": handle_read_sensor,
    "read_all_sensors": handle_read_all_sensors,
    "get_alarms": handle_get_alarms,
    "get_trend": handle_get_trend,
    "get_device_status": handle_get_device_status,
}


def call(name: str, args: dict) -> dict:
    """执行工具调用"""
    handler = HANDLERS.get(name)
    if not handler:
        return {"ok": False, "error": f"未知工具 '{name}'", "summary": f"未知工具 '{name}'"}
    try:
        return handler(args)
    except Exception as e:
        return {"ok": False, "error": str(e), "summary": f"工具执行出错：{e}"}
