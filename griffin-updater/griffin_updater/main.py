from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from . import config, theme
from .ui.main_window import MainWindow


def main() -> int:
    config.ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName("Griffin Updater")
    app.setQuitOnLastWindowClosed(False)  # keep running in tray for scheduled checks
    app.setStyleSheet(theme.STYLESHEET)
    if config.APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(config.APP_ICON_PATH)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
