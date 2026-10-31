from __future__ import annotations

import sys

from . import config


def main() -> int:
    # Allow the same binary (including the AppImage) to act as the CLI so
    # systemd --user units can invoke checks without the GUI process being
    # alive.  Subcommands match griffin_updater.cli.
    if len(sys.argv) > 1 and sys.argv[1] in ("check", "check-all", "install-timers"):
        from .cli import main as cli_main
        return cli_main()

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    from . import theme
    from .ui.main_window import MainWindow

    config.ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName("Griffin Updater")
    app.setQuitOnLastWindowClosed(False)  # keep running in tray when the window is closed
    app.setStyleSheet(theme.STYLESHEET)
    if config.APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(config.APP_ICON_PATH)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
