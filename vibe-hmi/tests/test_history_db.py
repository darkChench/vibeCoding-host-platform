"""
历史数据库测试

验证核心前提：samples 按 device_id 隔离——多设备写入后，
按设备查询互不串扰（历史页"按设备查询"功能依赖此语义）。

运行：
    cd vibe-hmi
    .venv/Scripts/python.exe -m pytest tests/test_history_db.py -v
"""
import pytest

from src import history_db


@pytest.fixture
def tmp_db(monkeypatch, tmp_path):
    """把历史库指到临时目录，不碰真实 save/history.db"""
    monkeypatch.setattr(history_db, "_DB_DIR", str(tmp_path))
    monkeypatch.setattr(history_db, "DB_PATH", str(tmp_path / "history.db"))


class TestDeviceIsolation:
    def test_query_isolated_by_device(self, tmp_db):
        """两台设备写同名参数，按设备查询只返回各自的记录。"""
        history_db.insert_batch("dev-001", {"temperature": 25.5, "density": 5.2},
                                "2026-10-22 10:00:00.000")
        history_db.insert_batch("dev-002", {"temperature": 31.0},
                                "2026-10-22 10:00:01.000")

        rows_1 = history_db.query(device_id="dev-001")
        rows_2 = history_db.query(device_id="dev-002")

        assert {(r["param_name"], r["value"]) for r in rows_1} == {
            ("temperature", 25.5), ("density", 5.2)}
        assert {(r["param_name"], r["value"]) for r in rows_2} == {
            ("temperature", 31.0)}

    def test_same_param_different_devices_not_mixed(self, tmp_db):
        """时间范围 + 参数过滤叠加设备过滤：不混入另一台设备的同名参数。"""
        for i in range(3):
            history_db.insert_batch("dev-001", {"pressure": round(0.40 + i * 0.01, 2)},
                                    f"2026-10-22 10:00:0{i}.000")
            history_db.insert_batch("dev-002", {"pressure": 0.99},
                                    f"2026-10-22 10:00:0{i}.500")

        rows = history_db.query(
            device_id="dev-001", param_names=["pressure"],
            start_time="2026-10-22 00:00:00.000", end_time="2026-10-22 23:59:59.000")
        # 只有 dev-001 的 3 条，dev-002 的 3 条不得混入
        assert [r["value"] for r in rows] == [0.40, 0.41, 0.42]

    def test_get_devices_lists_devices_with_data(self, tmp_db):
        """get_devices 返回有数据的设备 ID（无数据的不出现）。"""
        history_db.insert_batch("dev-001", {"temperature": 1.0})
        history_db.insert_batch("dev-004", {"temperature": 2.0})
        assert history_db.get_devices() == ["dev-001", "dev-004"]


class TestDeleteDeviceData:
    """按设备删除（全部 / 时间范围），采样与报警同事务删除。"""

    def test_count_device_data_with_unacked(self, tmp_db):
        """预览计数：采样/报警/未确认报警分开统计。"""
        history_db.insert_batch("dev-001", {"temperature": 25.0}, "2026-10-22 10:00:00.000")
        a1 = history_db.insert_alarm("dev-001", "温度高", "warning", "2026-10-22 10:00:01.000")
        history_db.insert_alarm("dev-001", "温度低", "critical", "2026-10-22 10:00:02.000")
        history_db.acknowledge_alarms([a1])

        cnt = history_db.count_device_data("dev-001")
        assert cnt == {"samples": 1, "alarms": 2, "unacked": 1}

    def test_delete_all_only_target_device(self, tmp_db):
        """全部删除：只删目标设备的采样+报警，其他设备不受影响。"""
        history_db.insert_batch("dev-001", {"temperature": 1.0}, "2026-10-22 10:00:00.000")
        history_db.insert_alarm("dev-001", "报警A", "warning", "2026-10-22 10:00:01.000")
        history_db.insert_batch("dev-002", {"temperature": 2.0}, "2026-10-22 10:00:02.000")
        history_db.insert_alarm("dev-002", "报警B", "critical", "2026-10-22 10:00:03.000")

        result = history_db.delete_device_data("dev-001")
        assert result == {"samples": 1, "alarms": 1}
        assert history_db.count_device_data("dev-001") == {"samples": 0, "alarms": 0, "unacked": 0}
        assert history_db.count_device_data("dev-002") == {"samples": 1, "alarms": 1, "unacked": 1}

    def test_delete_by_time_range_keeps_outside(self, tmp_db):
        """按时间范围删除：范围外（早于/晚于）的采样和报警保留。"""
        for ts in ("2026-10-22 09:00:00.000", "2026-10-22 10:00:00.000", "2026-10-22 11:00:00.000"):
            history_db.insert_batch("dev-001", {"temperature": 1.0}, ts)
        history_db.insert_alarm("dev-001", "范围内报警", "warning", "2026-10-22 10:00:00.000")
        history_db.insert_alarm("dev-001", "范围外报警", "warning", "2026-10-22 11:00:00.000")

        result = history_db.delete_device_data(
            "dev-001",
            start_time="2026-10-22 09:30:00",
            end_time="2026-10-22 10:30:00",
        )
        assert result == {"samples": 1, "alarms": 1}
        # 剩 09:00 和 11:00 两条采样、11:00 一条报警
        assert history_db.count_device_data("dev-001") == {"samples": 2, "alarms": 1, "unacked": 1}
