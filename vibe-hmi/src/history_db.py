"""
历史数据库

用 SQLite 存储采样数据，支持时间范围查询和点位筛选。
数据库文件：./save/history.db（无需安装，Python 内置 sqlite3）。

表结构：
  samples(id, device_id, param_name, timestamp, value)
  - timestamp: ISO8601 格式 "YYYY-MM-DD HH:MM:SS.mmm"
  - value: float 工程值
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional

# 数据库文件路径
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "save")
DB_PATH = os.path.join(_DB_DIR, "history.db")


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（自动建库建表）"""
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # 建表（IF NOT EXISTS）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            param_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            value REAL NOT NULL
        )
    """)
    # 时间索引（加速时间范围查询）
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_samples_timestamp ON samples(timestamp)
    """)
    # 复合索引（加速点位+时间查询）
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_samples_param_time
        ON samples(device_id, param_name, timestamp)
    """)
    conn.commit()
    return conn


def insert_sample(device_id: str, param_name: str, value: float, ts: Optional[str] = None):
    """写入一条采样数据"""
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO samples (device_id, param_name, timestamp, value) VALUES (?, ?, ?, ?)",
            (device_id, param_name, ts, value),
        )
        conn.commit()
    finally:
        conn.close()


def insert_batch(device_id: str, data: dict[str, float], ts: Optional[str] = None):
    """批量写入一轮采样数据。

    data: {param_name: value}
    过滤 None / NaN 值，避免 NOT NULL 约束失败。
    """
    import math
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    # 过滤掉 None / NaN / Inf 值
    items = []
    for name, val in data.items():
        if val is None:
            continue
        try:
            fval = float(val)
            if math.isnan(fval) or math.isinf(fval):
                continue
            items.append((device_id, name, ts, fval))
        except (ValueError, TypeError):
            continue
    if not items:
        return
    conn = _get_conn()
    try:
        conn.executemany(
            "INSERT INTO samples (device_id, param_name, timestamp, value) VALUES (?, ?, ?, ?)",
            items,
        )
        conn.commit()
    finally:
        conn.close()


def query(
    device_id: Optional[str] = None,
    param_names: Optional[list[str]] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> list[dict]:
    """查询历史数据。

    返回 [{param_name, timestamp, value}, ...]，按时间排序。
    """
    conn = _get_conn()
    try:
        sql = "SELECT param_name, timestamp, value FROM samples WHERE 1=1"
        params = []
        if device_id:
            sql += " AND device_id = ?"
            params.append(device_id)
        if param_names:
            placeholders = ",".join("?" * len(param_names))
            sql += f" AND param_name IN ({placeholders})"
            params.extend(param_names)
        if start_time:
            sql += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            sql += " AND timestamp <= ?"
            params.append(end_time)
        sql += " ORDER BY timestamp ASC"
        rows = conn.execute(sql, params).fetchall()
        return [{"param_name": r["param_name"], "timestamp": r["timestamp"], "value": r["value"]} for r in rows]
    finally:
        conn.close()


def get_param_names(device_id: Optional[str] = None) -> list[str]:
    """获取有数据记录的参数名列表"""
    conn = _get_conn()
    try:
        if device_id:
            rows = conn.execute(
                "SELECT DISTINCT param_name FROM samples WHERE device_id = ? ORDER BY param_name",
                (device_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT param_name FROM samples ORDER BY param_name"
            ).fetchall()
        return [r["param_name"] for r in rows]
    finally:
        conn.close()


def get_devices() -> list[str]:
    """获取有数据记录的设备 ID 列表"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT device_id FROM samples ORDER BY device_id"
        ).fetchall()
        return [r["device_id"] for r in rows]
    finally:
        conn.close()


def get_record_count() -> int:
    """获取总记录数"""
    conn = _get_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
    finally:
        conn.close()


def clear_all():
    """清空所有历史数据"""
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM samples")
        conn.execute("VACUUM")  # 压缩数据库文件
        conn.commit()
    finally:
        conn.close()
