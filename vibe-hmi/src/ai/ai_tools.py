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
    {
        "type": "function",
        "function": {
            "name": "query_history",
            "description": (
                "查询历史采样数据库。可查总数、时间范围，或取指定参数的历史数据做统计分析"
                "（均值/方差/极值/趋势等）。当用户问'有多少条数据/时间跨度/统计某个量'时用此工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "point": {
                        "type": "string",
                        "description": "采样点名称（如温度、压力）。不传则统计所有参数。",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "开始时间，格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS（可选）",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "结束时间，格式同上（可选）",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回的数据点数量上限（默认 50，避免数据过多）。仅用于取数据序列时；统计总数/时间范围不受此限。",
                    },
                },
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


def _downsample_rows(rows: list[dict], limit: int) -> list[dict]:
    """等间隔降采样：保留首尾点，中间按步长均匀取点。

    与"只取最近 limit 个"不同，等间隔抽样能让 limit 个点均匀覆盖整个时间范围，
    反映整体趋势而非只看最近一段。数据量 ≤ limit 时原样返回。
    """
    n = len(rows)
    if n <= limit or limit <= 0:
        return rows
    step = n / limit
    # 保留首尾 + 中间等间隔索引，去重排序
    indices = sorted(set(int(i * step) for i in range(limit)) | {n - 1})
    return [rows[i] for i in indices]


def _compute_stats(values: list[float], decimals: int) -> dict:
    """用 Python 确定性地计算统计量（基于全部有效数据点）。

    LLM 自己算统计量容易出错（它是语言模型，靠猜而非真算），
    这里用标准库数学函数算准，LLM 只需解读结果。
    返回 dict，所有数值已按 decimals 四舍五入。
    """
    import math
    n = len(values)
    if n == 0:
        return {"count": 0}
    mean = sum(values) / n
    # 总体方差 σ² = Σ(xi - μ)² / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)
    lo = min(values)
    hi = max(values)
    return {
        "count": n,
        "mean": round(mean, decimals + 2),       # 均值多留2位，统计更准
        "variance": round(variance, decimals + 4),
        "std": round(std, decimals + 2),         # 标准差
        "min": round(lo, decimals),
        "max": round(hi, decimals),
        "range": round(hi - lo, decimals),       # 极差
    }


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
    """查询趋势数据：查询全部历史点，用 Python 算准统计量返回，LLM 只解读。

    统计量（均值/方差/标准差/极值）基于全部有效数据点确定性计算，
    LLM 直接引用即可，不再自己算（语言模型算统计易出错）。
    降采样序列仅供描述走势。
    """
    from ..history_db import query as db_query

    point = args.get("point", "")
    p = _find_param_by_display(point)
    if not p:
        return {"ok": False, "error": f"未找到采样点 '{point}'", "summary": f"未找到采样点 '{point}'"}

    all_rows = db_query(
        device_id=store.current_device_id,
        param_names=[p["name"]],
    )

    display = p.get("display", p["name"])
    unit = p.get("unit", "")
    decimals = int(p.get("decimals", 0))

    if not all_rows:
        return {
            "ok": True,
            "data": {"point": display, "unit": unit, "points": [], "statistics": {"count": 0}},
            "summary": f"暂无 {display} 的历史趋势数据",
        }

    # 有效值用于 Python 确定性计算统计量
    valid_values = [r["value"] for r in all_rows if r["value"] is not None]
    computed = _compute_stats(valid_values, decimals)

    # 降采样序列（仅描述走势，统计量已基于全部点算准）
    sampled = _downsample_rows(all_rows, 50)
    value_strs = [f"{r['value']:.{decimals}f}" for r in sampled]
    time_span = f"（覆盖时段：{sampled[0]['timestamp']} ~ {sampled[-1]['timestamp']}）"

    # summary：统计块（准确数字）+ 趋势序列（参考）
    summary = (
        f"{display}（单位：{unit}）历史趋势：\n"
        f"统计量（已基于全部 {computed['count']} 个有效数据点计算，请直接引用，勿自行重算）：\n"
        f"  均值 μ = {computed['mean']} {unit}\n"
        f"  标准差 σ = {computed['std']} {unit}\n"
        f"  方差 σ² = {computed['variance']}\n"
        f"  最大值 = {computed['max']} {unit}\n"
        f"  最小值 = {computed['min']} {unit}\n"
        f"  极差 = {computed['range']} {unit}\n"
        f"等间隔抽取 {len(sampled)} 个点的趋势序列{time_span}（仅供描述走势）：\n"
        + ", ".join(value_strs)
    )

    return {
        "ok": True,
        "data": {
            "point": display, "unit": unit,
            "statistics": computed,  # Python 算好的准确统计量
            "points": [{"timestamp": r["timestamp"], "value": r["value"]} for r in sampled],
        },
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


def handle_query_history(args: dict) -> dict:
    """查询历史数据库：总数、时间范围，可选取数据序列做统计分析。

    始终返回统计信息（条数、最早/最晚时间）；
    若指定了参数且有条数，同时返回该参数的数据序列（受 limit 限制），
    供 LLM 做均值/方差/极值等计算。value 为 NULL（采到但无效）的记录
    在统计总数时计入，但在数据序列中标注为 null。
    """
    from ..history_db import query as db_query, stats as db_stats

    point = args.get("point", "")
    start_time = args.get("start_time") or None
    end_time = args.get("end_time") or None
    limit = int(args.get("limit", 50))

    # 定位参数（point 为空时统计所有参数）
    p = _find_param_by_display(point) if point else None
    param_name = p["name"] if p else None
    display = p.get("display", p["name"]) if p else (point or "全部参数")

    # 统计：总数 + 时间范围（不受 limit 限制）
    stat = db_stats(
        device_id=store.current_device_id,
        param_name=param_name,
    )

    # 取数据序列：查询全部点，用 Python 算准统计量，降采样序列仅作趋势参考
    data_points: list = []
    stats_block = ""
    series_summary = ""
    computed: dict = {}
    if param_name and stat["count"] > 0:
        all_rows = db_query(
            device_id=store.current_device_id,
            param_names=[param_name],
            start_time=start_time,
            end_time=end_time,
        )
        decimals = int(p.get("decimals", 0)) if p else 2
        unit = p.get("unit", "") if p else ""

        # 有效值（过滤 NULL），用于 Python 确定性计算统计量
        valid_values = [r["value"] for r in all_rows if r["value"] is not None]
        computed = _compute_stats(valid_values, decimals)

        # 降采样序列（仅作趋势形状参考，统计量已基于全部点算准）
        sampled = _downsample_rows(all_rows, limit)
        data_points = [
            {"timestamp": r["timestamp"],
             "value": (round(r["value"], decimals) if r["value"] is not None else None)}
            for r in sampled
        ]

        # 统计块：给 LLM 准确的数字（Python 算好，LLM 直接引用，不要自己重算）
        if computed.get("count", 0) > 0:
            stats_block = (
                f"\n统计量（已基于全部 {computed['count']} 个有效数据点计算，"
                f"请直接引用以下数值，不要自行重新计算）：\n"
                f"  均值 μ = {computed['mean']} {unit}\n"
                f"  标准差 σ = {computed['std']} {unit}\n"
                f"  方差 σ² = {computed['variance']}\n"
                f"  最大值 = {computed['max']} {unit}\n"
                f"  最小值 = {computed['min']} {unit}\n"
                f"  极差 = {computed['range']} {unit}"
            )

        # 趋势序列（降采样后，让 LLM 描述走势，不用于算统计）
        value_strs = [
            ("null" if r["value"] is None else f"{r['value']:.{decimals}f}")
            for r in sampled
        ]
        time_span = ""
        if sampled:
            time_span = f"（覆盖时段：{sampled[0]['timestamp']} ~ {sampled[-1]['timestamp']}）"
        series_summary = (
            f"\n{display}（单位：{unit}）等间隔抽取 {len(sampled)} 个点的趋势序列{time_span}，"
            f"仅供描述走势（统计量见上，勿用此序列重算）：\n"
            + ", ".join(value_strs)
        )

    # 组装 summary：统计信息 + 准确统计量块 + 趋势序列
    parts = [
        f"{display} 历史数据统计：",
        f"  总记录数：{stat['count']} 条",
    ]
    if stat["count"] > 0:
        parts.append(f"  最早时间：{stat['earliest']}")
        parts.append(f"  最晚时间：{stat['latest']}")
        if start_time or end_time:
            scope = f"  查询范围：{start_time or '不限'} 至 {end_time or '不限'}"
            parts.append(scope)
    if stats_block:
        parts.append(stats_block)
    if series_summary:
        parts.append(series_summary)
    summary = "\n".join(s for s in parts if s)

    return {
        "ok": True,
        "data": {
            "point": display,
            "count": stat["count"],
            "earliest": stat["earliest"],
            "latest": stat["latest"],
            "query_range": {"start": start_time, "end": end_time},
            "statistics": computed,  # Python 算好的准确统计量（均值/方差/标准差/极值）
            "points": data_points,   # 降采样序列，仅作趋势参考
        },
        "summary": summary,
    }


# ===== 工具分发 =====

HANDLERS = {
    "read_sensor": handle_read_sensor,
    "read_all_sensors": handle_read_all_sensors,
    "get_alarms": handle_get_alarms,
    "get_trend": handle_get_trend,
    "get_device_status": handle_get_device_status,
    "query_history": handle_query_history,
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
