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
from datetime import datetime, timedelta
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

    # ===== 报警记录表（与 samples 同库，统一管理/备份）=====
    # 全新表，旧库打开时 IF NOT EXISTS 自动建出，无需迁移
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            device_id TEXT NOT NULL,
            content TEXT NOT NULL,
            level TEXT NOT NULL,
            acknowledged INTEGER NOT NULL DEFAULT 0,
            ack_user TEXT,
            ack_time TEXT
        )
    """)
    # 时间索引（加速时间范围查询 + 排序）
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_alarms_timestamp ON alarms(timestamp)
    """)
    # 确认状态复合索引（加速"未确认"筛选，侧边栏未确认数常查）
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_alarms_ack ON alarms(acknowledged, timestamp)
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


def purge_expired(retention_days: int) -> int:
    """删除超过保留天数的过期数据，返回删除条数。

    按当前时间往前推 retention_days 天作为截止线，早于此时间的记录删除。
    retention_days <= 0 表示永久保留，直接返回 0 不做任何操作。
    删除后执行 VACUUM 压缩数据库文件，释放磁盘空间。

    用于应用启动时和定期清理，控制数据库无限增长。
    """
    if retention_days <= 0:
        return 0
    cutoff = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM samples WHERE timestamp < ?", (cutoff,))
        deleted = cur.rowcount
        conn.commit()
        # 有删除才 VACUUM（VACUUM 会重写整个数据库文件，较耗时，避免无意义执行）
        if deleted > 0:
            conn.execute("VACUUM")
        conn.commit()
        return deleted
    finally:
        conn.close()


# ============================================================
# 报警记录 CRUD（alarms 表）
# 模式与 samples 一致：_get_conn() + try/commit/finally close + ? 参数化
# ============================================================

def insert_alarm(device_id: str, content: str, level: str, ts: Optional[str] = None) -> int:
    """插入一条报警，返回新 id（cursor.lastrowid）。

    ts 缺省用当前时间（毫秒精度，对齐 samples 时间格式）。
    acknowledged 默认 0（未确认）。
    """
    if ts is None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO alarms (timestamp, device_id, content, level, acknowledged) VALUES (?, ?, ?, ?, 0)",
            (ts, device_id, content, level),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def query_alarms(
    device_id: Optional[str] = None,
    level: Optional[str] = None,
    unacknowledged: Optional[bool] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    """查询报警记录，按时间倒序（最新在前）。

    所有参数可选，组合过滤。返回 [{id, timestamp, device_id, content, level,
    acknowledged(bool), ack_user, ack_time}, ...]。
    """
    conn = _get_conn()
    try:
        sql = "SELECT id, timestamp, device_id, content, level, acknowledged, ack_user, ack_time FROM alarms WHERE 1=1"
        params: list = []
        if device_id:
            sql += " AND device_id = ?"
            params.append(device_id)
        if level:
            sql += " AND level = ?"
            params.append(level)
        if unacknowledged is True:
            sql += " AND acknowledged = 0"
        if start_time:
            sql += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            sql += " AND timestamp <= ?"
            params.append(end_time)
        sql += " ORDER BY timestamp DESC"  # 最新在前（报警页默认看最新的）
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [{
            "id": r["id"],
            "time": r["timestamp"],        # 对齐 store.alarms 的字段名（UI 用 time）
            "device_id": r["device_id"],
            "content": r["content"],
            "level": r["level"],
            "acknowledged": bool(r["acknowledged"]),
            "ack_user": r["ack_user"] or "",
            "ack_time": r["ack_time"] or "",
            # 兼容字段：UI 的 COLS 用 "terminal"，历史报警曾用此名
            "terminal": r["device_id"],
        } for r in rows]
    finally:
        conn.close()


def acknowledge_alarms(alarm_ids: list[int], user: str = "工程师") -> int:
    """确认多条报警（UPDATE，本文件首个更新语句）。

    只更新未确认的（acknowledged=0），保证幂等。
    ack_time 用毫秒精度完整时间（对齐 samples，含日期，比旧版"H:M:S"更完整）。
    返回实际更新条数。
    """
    if not alarm_ids:
        return 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    placeholders = ",".join("?" * len(alarm_ids))
    conn = _get_conn()
    try:
        cur = conn.execute(
            f"""UPDATE alarms
                SET acknowledged = 1, ack_user = ?, ack_time = ?
                WHERE id IN ({placeholders}) AND acknowledged = 0""",
            [user, now, *alarm_ids],
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def get_unack_count(device_id: Optional[str] = None) -> int:
    """未确认报警数（侧边栏/状态栏常查）。"""
    conn = _get_conn()
    try:
        if device_id:
            row = conn.execute(
                "SELECT COUNT(*) FROM alarms WHERE acknowledged = 0 AND device_id = ?",
                (device_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM alarms WHERE acknowledged = 0"
            ).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def delete_alarm(alarm_id: int) -> bool:
    """删除单条报警，返回是否删除成功。"""
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def clear_all_alarms() -> int:
    """清空所有报警，返回删除条数。"""
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM alarms")
        deleted = cur.rowcount
        conn.commit()
        if deleted > 0:
            conn.execute("VACUUM")
        conn.commit()
        return deleted
    finally:
        conn.close()


def purge_expired_alarms(retention_days: int) -> int:
    """删除超过保留天数的过期报警，返回删除条数（与 samples 保留策略一致）。"""
    if retention_days <= 0:
        return 0
    cutoff = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM alarms WHERE timestamp < ?", (cutoff,))
        deleted = cur.rowcount
        conn.commit()
        if deleted > 0:
            conn.execute("VACUUM")
        conn.commit()
        return deleted
    finally:
        conn.close()
