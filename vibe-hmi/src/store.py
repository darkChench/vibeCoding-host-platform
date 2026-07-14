"""
状态层

管理运行时可变状态：参数表/报警/连接状态/slave_id/筛选等。
参数表持久化到 config/params.json。
对应原型 store.js。
"""
import json
import os
from dataclasses import dataclass, asdict, field
from typing import Optional

# 参数表文件路径
PARAMS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "params.json")

# 默认参数表（首次运行或配置丢失时回退）
DEFAULT_PARAMS = [
    {
        "name": "temperature", "display": "温度", "address": "0x0000",
        "category": "采样参数", "type": "float32", "access": "只读",
        "unit": "℃", "decimals": 1, "min": -40, "max": 125, "desc": "缩放 0.1",
    },
    {
        "name": "pressure", "display": "压力", "address": "0x0002",
        "category": "采样参数", "type": "float32", "access": "只读",
        "unit": "MPa", "decimals": 2, "min": 0, "max": 60, "desc": "缩放 0.01",
    },
    {
        "name": "sample_period", "display": "采样周期", "address": "0x0010",
        "category": "配置参数", "type": "uint16", "access": "读写",
        "unit": "ms", "decimals": 0, "min": 200, "max": 5000, "desc": "写入需确认",
    },
    {
        "name": "device_addr", "display": "设备地址", "address": "0x0011",
        "category": "配置参数", "type": "uint8", "access": "读写",
        "unit": "-", "decimals": 0, "min": 1, "max": 247, "desc": "Modbus 从站地址",
    },
]


class Store:
    """全局状态管理"""

    def __init__(self):
        # 参数表
        self.params: list[dict] = []
        self.params_dirty: bool = False
        self.param_filter: str = "all"  # 'all' | '采样参数' | '配置参数'
        # 曲线显隐：{param_name: bool}，缺省视为 True（显示）
        self.curve_visible: dict[str, bool] = {}

        # 连接状态
        self.connection_state: str = "connected"
        self.slave_id: int = 1
        self.current_port: str = "COM3"

        # 加载持久化数据
        self._load_params()

    def _load_params(self):
        """从 config/params.json 加载参数表，失败回退默认"""
        try:
            if os.path.exists(PARAMS_FILE):
                with open(PARAMS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        self.params = data
                        return
        except Exception:
            pass
        # 回退默认
        self.params = [dict(p) for p in DEFAULT_PARAMS]

    def save_params(self):
        """持久化参数表到 config/params.json"""
        try:
            os.makedirs(os.path.dirname(PARAMS_FILE), exist_ok=True)
            with open(PARAMS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.params, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def sample_params(self) -> list[dict]:
        """取采样参数（category == '采样参数'）"""
        return [p for p in self.params if p.get("category") == "采样参数"]

    def filtered_params(self) -> list[dict]:
        """按当前筛选条件过滤后的参数列表"""
        if self.param_filter == "all":
            return self.params
        return [p for p in self.params if p.get("category") == self.param_filter]

    def find_param(self, name: str) -> Optional[dict]:
        """按 name 查找参数"""
        for p in self.params:
            if p.get("name") == name:
                return p
        return None

    def get_curve_visible(self, name: str) -> bool:
        """取某采样参数曲线是否显示（缺省 True）"""
        return self.curve_visible.get(name, True)

    def validate_param(self, data: dict, exclude_name: str = None) -> dict:
        """校验参数定义，返回 {ok: bool, errors: {field: msg}}"""
        errors = {}
        name = data.get("name", "").strip()

        if not name:
            errors["name"] = "参数名不能为空"
        elif not name.replace("_", "").isalnum() or name[0].isdigit():
            errors["name"] = "仅允许字母数字下划线，且不以数字开头"
        else:
            for p in self.params:
                if p["name"] == name and p["name"] != exclude_name:
                    errors["name"] = f'参数名 "{name}" 已存在'
                    break

        # 显示名必填
        if not data.get("display", "").strip():
            errors["display"] = "显示名不能为空"

        address = data.get("address", "").strip()
        if not address:
            errors["address"] = "地址不能为空"
        elif not address.startswith("0x"):
            errors["address"] = "地址格式应为 0x0000~0xFFFF"
        else:
            try:
                addr_val = int(address, 16)
                if not (0 <= addr_val <= 0xFFFF):
                    errors["address"] = "地址范围 0x0000~0xFFFF"
                else:
                    for p in self.params:
                        if p["address"].lower() == address.lower() and p["name"] != exclude_name:
                            errors["address"] = f'地址 {address} 已被 "{p["name"]}" 占用'
                            break
            except ValueError:
                errors["address"] = "地址格式非法"

        if data.get("type") not in ("uint8", "int16", "uint16", "int32", "uint32", "float32", "bool"):
            errors["type"] = "数据类型非法"

        if data.get("access") not in ("只读", "只写", "读写"):
            errors["access"] = "访问权限非法"

        # 单位必填
        if not data.get("unit", "").strip():
            errors["unit"] = "单位不能为空"

        try:
            decimals = int(data.get("decimals", 0))
            if decimals < 0:
                errors["decimals"] = "小数位须为非负整数"
        except (ValueError, TypeError):
            errors["decimals"] = "小数位须为整数"

        # 最小值/最大值/说明不校验（选填）

        return {"ok": len(errors) == 0, "errors": errors}


# 全局单例
store = Store()
