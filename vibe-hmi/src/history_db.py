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

from . import paths

# 数据库文件路径(开发模式=项目根/save,打包模式=exe 同级/save)
_DB_DIR = os.path.join(paths.app_root(), "save")
DB_PATH = os.path.join(_DB_DIR, "history.db")


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（自动建库建表）

    value 列允许 NULL：表示该参数本轮采到了但值为无效（NaN/Inf/解析失败）。
    这样"微水"等恒为 NaN 的参数也能留痕，导出时按空值显示，不会丢失参数列。
    """
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # 建表（IF NOT EXISTS）—— value 允许 NULL
    conn.execute("""
        CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            param_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            value REAL
        )
    """)
    # 迁移：旧库的 value 列可能是 NOT NULL，需重建表去掉约束
    _migrate_drop_value_notnull(conn)
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


def _migrate_drop_value_notnull(conn: sqlite3.Connection):
    """迁移：若旧库 value 列是 NOT NULL，则重建表去掉约束（允许存 NULL）。

    SQLite 不支持 ALTER COLUMN，需走 建新表→复制→重命名 的标准迁移流程。
    通过 PRAGMA 检测列约束，仅在必要时执行，幂等。
    """
    # 检测 value 列是否 NOT NULL
    cols = conn.execute("PRAGMA table_info(samples)").fetchall()
    if not cols:
        return  # 表不存在（CREATE 在外层会建）
    value_col = next((c for c in cols if c["name"] == "value"), None)
    if not value_col or value_col["notnull"] == 0:
        return  # value 已允许 NULL，无需迁移
    # value 是 NOT NULL，需迁移
    conn.executescript("""
        CREATE TABLE samples_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            param_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            value REAL
        );
        INSERT INTO samples_new (id, device_id, param_name, timestamp, value)
        SELECT id, device_id, param_name, timestamp, value FROM samples;
        DROP TABLE samples;
        ALTER TABLE samples_new RENAME TO samples;
    """)


def insert_sample(device_id: str, param_name: str, value: float, ts: Optional[str] = None):
    """写入一条采样数据。

    NaN / Inf / None 值存为 NULL（表示该参数本轮采到了但值无效，留痕用于导出）。
    """
    import math
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    # 无效值转 NULL
    store_value = None
    if value is not None:
        try:
            fval = float(value)
            if not (math.isnan(fval) or math.isinf(fval)):
                store_value = fval
        except (ValueError, TypeError):
            pass  # 保持 None
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO samples (device_id, param_name, timestamp, value) VALUES (?, ?, ?, ?)",
            (device_id, param_name, ts, store_value),
        )
        conn.commit()
    finally:
        conn.close()


def insert_batch(device_id: str, data: dict[str, float], ts: Optional[str] = None):
    """批量写入一轮采样数据。

    data: {param_name: value}
    NaN / Inf / None 值存为 NULL（保留参数留痕，导出时不丢失该参数列）。
    """
    import math
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    items = []
    for name, val in data.items():
        store_value = None
        if val is not None:
            try:
                fval = float(val)
                if not (math.isnan(fval) or math.isinf(fval)):
                    store_value = fval
            except (ValueError, TypeError):
                pass  # 保持 None
        items.append((device_id, name, ts, store_value))
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


def stats(
    device_id: Optional[str] = None,
    param_name: Optional[str] = None,
) -> dict:
    """查询历史数据的统计信息：总条数、最早/最晚时间戳。

    用于 AI 助手回答"有多少条数据、时间跨度"等问题。
    value 为 NULL 的记录（采到但无效）也计入条数。

    返回 {count, earliest, latest}，无数据时 count=0、时间为 None。
    """
    conn = _get_conn()
    try:
        sql = "SELECT COUNT(*) AS cnt, MIN(timestamp) AS t_min, MAX(timestamp) AS t_max FROM samples WHERE 1=1"
        params: list = []
        if device_id:
            sql += " AND device_id = ?"
            params.append(device_id)
        if param_name:
            sql += " AND param_name = ?"
            params.append(param_name)
        row = conn.execute(sql, params).fetchone()
        if not row:
            return {"count": 0, "earliest": None, "latest": None}
        return {
            "count": row["cnt"] or 0,
            "earliest": row["t_min"],
            "latest": row["t_max"],
        }
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
