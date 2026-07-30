"""
路径解析(开发模式 / 打包模式 双感知)

PyInstaller frozen 后,`__file__` 指向只读临时目录 _MEIPASS,
config/save/history 等用户数据目录不能用 __file__ 反推,
必须用 sys.executable(打包后 = exe 所在目录)。
开发模式下两者都等价于项目根目录(vibe-hmi/)。

参考:https://pyinstaller.org/en/stable/runtime-information.html
"""
import os
import sys


def app_root() -> str:
    """返回应用根目录(可写)。

    - 开发模式: vibe-hmi/(本文件位于 src/paths.py,往上 1 层即项目根)
    - 打包模式: exe 所在目录(sys.executable 的 dirname)
    """
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后:exe 所在目录
        return os.path.dirname(sys.executable)
    # 开发模式:项目根(src/ 的上一层)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_root() -> str:
    """返回只读资源根目录(图标、QSS 等随包资源)。

    - 开发模式: 同 app_root()(项目根)
    - 打包模式: _MEIPASS(PyInstaller 解压临时目录,含 --add-data 的文件)
    """
    if getattr(sys, "frozen", False):
        # 打包后:add-data 的资源在 _MEIPASS
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
