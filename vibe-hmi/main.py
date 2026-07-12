"""
multi-protocol-hmi 上位机入口

运行：
    cd vibe-hmi
    .venv/Scripts/python.exe main.py
"""
import sys
from PySide6.QtWidgets import QApplication

from src.style import build_qss
from src.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("multi-protocol-hmi")

    # 应用全局 QSS
    app.setStyleSheet(build_qss())

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
