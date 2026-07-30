# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 —— vibe-hmi 上位机

模式: onedir(单文件夹,启动快、易调试)
入口: main.py
产物: dist/vibe-hmi/vibe-hmi.exe

设计要点:
  1. collect_all('PySide6')  一键收集 Qt 全部插件(platforms/imageformats/styles/tls)
     + QtSvg.dll / QtCharts.dll 等动态库,避免目标机黑屏或图标失效
  2. hiddenimports 明确声明 QtSvg / QtCharts / serial.tools(延迟 import 易被漏)
  3. excludes 排除未使用的大依赖 pandas/openpyxl/pymodbus,体积减约 80MB
  4. arrow-down.svg 作为只读资源随包打进 _MEIPASS(通过 src/paths.py 的 resource_root() 定位)
  5. config/ save/ history/ 不打进包(用户数据外置,首次运行自动创建)

构建: 在 vibe-hmi/ 目录下执行 `pyinstaller vibe-hmi.spec --noconfirm`
      或直接运行 build.bat
"""
import os
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

# ===== 收集 PySide6 全部资源(插件/翻译/QML/DLL)=====
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")
pyside6_binaries += collect_dynamic_libs("PySide6")

# ===== 收集 pyserial 串口枚举模块 =====
serial_datas, serial_binaries, serial_hiddenimports = collect_all("serial")

# 注意:体积优化(剔除 WebEngine/QML/翻译等未用大文件)在 build.bat 的
# post-build 阶段执行。spec 阶段过滤会被 pyinstaller-hooks-contrib 的
# PySide6 hook 在 Analysis 之后无条件补回,无效。

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=pyside6_binaries + serial_binaries,
    datas=pyside6_datas + serial_datas + [
        # 只读资源:QComboBox 下拉箭头图标(随包进 _MEIPASS)
        ("assets/icons/arrow-down.svg", "assets/icons"),
    ],
    hiddenimports=[
        # Qt 扩展模块(代码用延迟 import,PyInstaller 静态分析易漏)
        "PySide6.QtSvg",          # src/icons.py 内联 SVG 渲染
        "PySide6.QtSvgWidgets",
        "PySide6.QtCharts",       # monitor/history 趋势曲线
        # pyserial 串口枚举(Windows 平台)
        "serial.tools.list_ports",
        "serial.tools.list_ports_common",
        "serial.tools.list_ports_windows",
        # HTTP 客户端(AI 助手调 LLM)
        "requests",
        "urllib3",
        "certifi",
        "charset_normalizer",
    ] + pyside6_hiddenimports + serial_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 未使用的大依赖(代码无 import,排除减体积)
        "pandas",
        "openpyxl",
        "pymodbus",
        # 无关标准库模块
        "tkinter",
        "unittest",
        "pydoc",
        "test",
        "distutils",
        "lib2to3",
        # PySide6 未使用的重型 Qt 模块(大幅减小体积)
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DExtras",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DRender",
        "PySide6.QtBluetooth",
        "PySide6.QtCharts3D",
        "PySide6.QtDataVisualization",
        "PySide6.QtDataVisualizationQml",
        "PySide6.QtDesigner",
        "PySide6.QtHelp",
        "PySide6.QtHttpServer",
        "PySide6.QtLocation",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtNetworkAuth",
        "PySide6.QtNfc",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtPositioning",
        "PySide6.QtPrintSupport",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickControls2",
        "PySide6.QtQuickWidgets",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSensors",
        "PySide6.QtSerialBus",
        "PySide6.QtSerialPort",
        "PySide6.QtSpatialAudio",
        "PySide6.QtSql",
        "PySide6.QtStateMachine",
        "PySide6.QtUiTools",
        "PySide6.QtVirtualKeyboard",
        "PySide6.QtWebChannel",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebSockets",
        "PySide6.QtWebView",
        "PySide6.QtWebViewQuick",
        "PySide6.QtWebViewWidgets",
        "PySide6.QtXml",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="vibe-hmi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 工业现场避免 UPX 被误杀
    console=False,  # GUI 程序,不弹控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icons/app.ico",  # TODO: 后续补充应用图标
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="vibe-hmi",
)
