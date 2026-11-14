"""
Desktop notifications.

Note: because scheduled checks run as `systemd --user` units (not root
cron/system units like the original discord-updater.service), the process
already inherits a working DBUS_SESSION_BUS_ADDRESS / XDG_RUNTIME_DIR from
the user session. That means we can call notify-send directly, no
sudo-per-logged-in-user dance required.
"""
from __future__ import annotations

import shutil
import subprocess

from .sysproc import host_env


def notify(title: str, message: str) -> None:
    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", "-a", "Griffin Updater", "-i", "system-software-update",
                 title, message],
                timeout=10, env=host_env(),
            )
            return
        except (OSError, subprocess.SubprocessError):
            pass
    # Fall back silently - the caller should already be writing to the log.
