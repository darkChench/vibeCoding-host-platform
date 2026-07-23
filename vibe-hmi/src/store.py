"""
状态层

管理运行时可变状态：设备列表/参数表/报警/连接状态/筛选等。
- 设备列表持久化到 config/devices.json
- 参数表按设备分组持久化到 config/params.json（{device_id: [param, ...]}）
对应原型 store.js。
"""
import json
import os
from typing import Optional

# 文件路径
_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
PARAMS_FILE = os.path.join(_config_dir, "params.json")
DEVICES_FILE = os.path.join(_config_dir, "devices.json")
HISTORY_FILE = os.path.join(_config_dir, "send_history.json")

# 默认参数表（首次运行或配置丢失时回退，挂在默认设备 dev-001 下）
DEFAULT_PARAMS = [
    {
        "name": "temperature", "display": "温度", "address": "0x0000",
        "category": "采样参数", "type": "float32", "access": "只读",
        "curve": "否", "unit": "℃", "decimals": 1, "min": -40, "max": 125, "desc": "缩放 0.1",
    },
    {
        "name": "pressure", "display": "压力", "address": "0x0002",
        "category": "采样参数", "type": "float32", "access": "只读",
        "curve": "否", "unit": "MPa", "decimals": 2, "min": 0, "max": 60, "desc": "缩放 0.01",
    },
    {
        "name": "sample_period", "display": "采样周期", "address": "0x0010",
        "category": "配置参数", "type": "uint16", "access": "读写",
        "curve": "否", "unit": "ms", "decimals": 0, "min": 200, "max": 5000, "desc": "写入需确认",
    },
    {
        "name": "device_addr", "display": "设备地址", "address": "0x0011",
        "category": "配置参数", "type": "uint8", "access": "读写",
        "curve": "否", "unit": "-", "decimals": 0, "min": 1, "max": 247, "desc": "Modbus 从站地址",
    },
]

# 默认设备列表
DEFAULT_DEVICES = [
    {"id": "dev-001", "name": "设备1", "slave_id": 1, "desc": "主设备", "location": ""},
]

# 默认报警记录（Ticket 07 报警记录页用）
DEFAULT_ALARMS = [
    {"id": 1, "time": "2026-07-17 10:23:45", "content": "压力接近上限 (0.098/0.100 MPa)",
     "terminal": "设备1", "level": "预警", "acknowledged": False},
    {"id": 2, "time": "2026-07-17 09:15:12", "content": "CRC 异常帧已丢弃",
     "terminal": "设备1", "level": "一般", "acknowledged": True,
     "ack_user": "工程师", "ack_time": "09:16:00"},
    {"id": 3, "time": "2026-07-17 08:30:00", "content": "备用终端离线超过 10 分钟",
     "terminal": "设备1", "level": "提示", "acknowledged": True,
     "ack_user": "工程师", "ack_time": "08:35:00"},
]


def _parse_addr(address: str) -> int:
    """解析寄存器地址（支持十进制 1000 和 16 进制 0x03E8）"""
    address = address.strip()
    if address.lower().startswith("0x"):
        return int(address, 16)
    return int(address, 10)


class Store:
    """全局状态管理"""

    def __init__(self):
        # 设备列表（持久化 devices.json）
        self.devices: list[dict] = []
        self.current_device_id: str = ""

        # 参数表：{device_id: [param, ...]}（持久化 params.json）
        self.params: dict[str, list[dict]] = {}
        self.param_filter: str = "all"  # 'all' | '采样参数' | '配置参数'
        # 曲线显隐：{param_name: bool}，缺省视为 True（显示）
        self.curve_visible: dict[str, bool] = {}

        # 连接状态
        self.connection_state: str = "disconnected"
        self.current_port: str = ""

        # 串口配置
        self.serial_config: dict = {
            "port": "COM3",
            "baudrate": 115200,
            "bytesize": 8,
            "parity": "N",
            "stopbits": 1,
            "timeout": 0.1,
        }

        # 发送历史（持久化）
        self.send_history: list[str] = []

        # 报警记录
        self.alarms: list[dict] = [dict(a) for a in DEFAULT_ALARMS]

        # 加载持久化数据
        self._load_devices()
        self._load_params()
        self._load_history()

        # 确保 current_device_id 有效
        if self.devices and not self.current_device_id:
            self.current_device_id = self.devices[0]["id"]

    # ===== 设备管理 =====

    def _load_devices(self):
        """从 config/devices.json 加载设备列表"""
        try:
            if os.path.exists(DEVICES_FILE):
                with open(DEVICES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        self.devices = data
                        return
        except Exception:
            pass
        # 回退默认
        self.devices = [dict(d) for d in DEFAULT_DEVICES]

    def save_devices(self):
        """持久化设备列表到 config/devices.json"""
        try:
            os.makedirs(_config_dir, exist_ok=True)
            with open(DEVICES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.devices, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_device(self, name: str, slave_id: int, desc: str = "", location: str = "") -> str:
        """新增设备，返回 device_id"""
        # 生成唯一 id
        max_num = 0
        for d in self.devices:
            if d["id"].startswith("dev-"):
                try:
                    num = int(d["id"][4:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        device_id = f"dev-{max_num + 1:03d}"
        self.devices.append({"id": device_id, "name": name, "slave_id": slave_id,
                             "desc": desc, "location": location})
        self.params[device_id] = []
        self.save_devices()
        self.save_params()
        return device_id

    def update_device(self, device_id: str, name: str, slave_id: int, desc: str = "", location: str = ""):
        """更新设备信息"""
        for d in self.devices:
            if d["id"] == device_id:
                d["name"] = name
                d["slave_id"] = slave_id
                d["desc"] = desc
                d["location"] = location
                break
        self.save_devices()

    def delete_device(self, device_id: str):
        """删除设备 + 该设备的参数"""
        self.devices = [d for d in self.devices if d["id"] != device_id]
        if device_id in self.params:
            del self.params[device_id]
        # 如果删的是当前设备，切换到第一个
        if self.current_device_id == device_id:
            self.current_device_id = self.devices[0]["id"] if self.devices else ""
        self.save_devices()
        self.save_params()

    def get_device(self, device_id: str = None) -> Optional[dict]:
        """取设备信息"""
        did = device_id or self.current_device_id
        for d in self.devices:
            if d["id"] == did:
                return d
        return None

    def get_slave_id(self, device_id: str = None) -> int:
        """取设备的从站地址"""
        d = self.get_device(device_id)
        return d.get("slave_id", 1) if d else 1

    def set_slave_id(self, slave_id: int, device_id: str = None):
        """更新设备的从站地址"""
        did = device_id or self.current_device_id
        for d in self.devices:
            if d["id"] == did:
                d["slave_id"] = slave_id
                self.save_devices()
                return

    def param_count(self, device_id: str = None) -> int:
        """取某设备的参数数量"""
        did = device_id or self.current_device_id
        return len(self.params.get(did, []))

    # ===== 参数管理 =====

    def _load_params(self):
        """从 config/params.json 加载参数表（按设备分组）。

        兼容旧格式（扁平数组）→ 自动迁移到 {"dev-001": [...]}。
        """
        try:
            if os.path.exists(PARAMS_FILE):
                with open(PARAMS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # 新格式：{device_id: [param, ...]}
                        self.params = data
                        # 确保每个设备都有对应的参数列表
                        for d in self.devices:
                            if d["id"] not in self.params:
                                self.params[d["id"]] = []
                        return
                    elif isinstance(data, list):
                        # 旧格式：扁平数组 → 迁移到第一个设备
                        first_id = self.devices[0]["id"] if self.devices else "dev-001"
                        self.params = {first_id: data}
                        for d in self.devices:
                            if d["id"] not in self.params:
                                self.params[d["id"]] = []
                        self.save_params()  # 保存迁移后的格式
                        return
        except Exception:
            pass
        # 回退默认（挂在第一个设备下）
        first_id = self.devices[0]["id"] if self.devices else "dev-001"
        self.params = {first_id: [dict(p) for p in DEFAULT_PARAMS]}

    def save_params(self):
        """持久化参数表到 config/params.json"""
        try:
            os.makedirs(_config_dir, exist_ok=True)
            with open(PARAMS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.params, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _cur_params(self, device_id: str = None) -> list[dict]:
        """取当前（或指定）设备的参数列表引用"""
        did = device_id or self.current_device_id
        if did not in self.params:
            self.params[did] = []
        return self.params[did]

    def sample_params(self, device_id: str = None) -> list[dict]:
        """取某设备的采样参数（category == '采样参数'）"""
        params = self._cur_params(device_id)
        return [p for p in params if p.get("category") == "采样参数"]

    def filtered_params(self, device_id: str = None) -> list[dict]:
        """按当前筛选条件过滤后的参数列表"""
        params = self._cur_params(device_id)
        if self.param_filter == "all":
            return params
        return [p for p in params if p.get("category") == self.param_filter]

    def find_param(self, name: str, device_id: str = None) -> Optional[dict]:
        """按 name 查找参数（在当前设备内）"""
        for p in self._cur_params(device_id):
            if p.get("name") == name:
                return p
        return None

    def get_curve_visible(self, name: str) -> bool:
        """取某采样参数曲线是否显示（缺省 True）"""
        return self.curve_visible.get(name, True)

    def validate_param(self, data: dict, device_id: str = None, exclude_name: str = None) -> dict:
        """校验参数定义（名称/地址在**同一设备内**唯一）"""
        errors = {}
        params = self._cur_params(device_id)
        name = data.get("name", "").strip()

        if not name:
            errors["name"] = "参数名不能为空"
        elif not name.replace("_", "").isalnum() or name[0].isdigit():
            errors["name"] = "仅允许字母数字下划线，且不以数字开头"
        else:
            for p in params:
                if p["name"] == name and p["name"] != exclude_name:
                    errors["name"] = f'参数名 "{name}" 已存在'
                    break

        if not data.get("display", "").strip():
            errors["display"] = "显示名不能为空"

        address = data.get("address", "").strip()
        if not address:
            errors["address"] = "地址不能为空"
        else:
            try:
                addr_val = _parse_addr(address)
                if not (0 <= addr_val <= 0xFFFF):
                    errors["address"] = "地址范围 0~65535"
                else:
                    for p in params:
                        try:
                            p_val = _parse_addr(p["address"])
                        except (ValueError, AttributeError):
                            continue
                        if p_val == addr_val and p["name"] != exclude_name:
                            errors["address"] = f'地址 {address} 已被 "{p["name"]}" 占用'
                            break
            except ValueError:
                errors["address"] = "地址格式非法（十进制如 1000，或 16 进制如 0x03E8）"

        if data.get("type") not in ("uint8", "int16", "uint16", "int32", "uint32", "float32", "bool"):
            errors["type"] = "数据类型非法"

        if data.get("access") not in ("只读", "只写", "读写"):
            errors["access"] = "访问权限非法"

        if not data.get("unit", "").strip():
            errors["unit"] = "单位不能为空"

        try:
            decimals = int(data.get("decimals", 0))
            if decimals < 0:
                errors["decimals"] = "小数位须为非负整数"
        except (ValueError, TypeError):
            errors["decimals"] = "小数位须为整数"

        return {"ok": len(errors) == 0, "errors": errors}

    # ===== 发送历史 =====

    def push_send_history(self, text: str, fmt: str = "HEX", ending: str = "无"):
        """发送历史：去重置顶，最多 20 条，持久化。"""
        text = text.strip()
        if not text:
            return
        entry = {"text": text, "fmt": fmt, "ending": ending}
        self.send_history = [e for e in self.send_history
                             if (e.get("text") if isinstance(e, dict) else e) != text]
        self.send_history.insert(0, entry)
        self.send_history = self.send_history[:20]
        self._save_history()

    def _load_history(self):
        """从 config/send_history.json 加载发送历史"""
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.send_history = data[:20]
        except Exception:
            pass

    def _save_history(self):
        """持久化发送历史"""
        try:
            os.makedirs(_config_dir, exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.send_history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ===== 报警 =====

    def unack_count(self) -> int:
        """未确认报警数"""
        return sum(1 for a in self.alarms if not a.get("acknowledged"))

    def acknowledge(self, alarm_ids: list[int], user: str = "工程师"):
        """确认报警（不可逆）"""
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        for a in self.alarms:
            if a["id"] in alarm_ids and not a.get("acknowledged"):
                a["acknowledged"] = True
                a["ack_user"] = user
                a["ack_time"] = now


# 全局单例
store = Store()
