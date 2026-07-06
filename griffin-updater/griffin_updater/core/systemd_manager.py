"""
Generates a `systemd --user` service+timer pair per tracked app, e.g.:

    ~/.config/systemd/user/griffin-updater-discord.service
    ~/.config/systemd/user/griffin-updater-discord.timer

This is the direct generalization of the discord-updater.service/.timer
pattern you already had, just templated per app id and with the schedule
computed from each app's Schedule object.

Because these are user units (not system units), notify-send works without
any of the /run/user/* sudo-loop workaround the original bash script needed.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .. import config
from ..models import AppEntry


def _unit_basename(app_id: str) -> str:
    return f"{config.UNIT_PREFIX}-{app_id}"


def service_path(app_id: str) -> Path:
    return config.SYSTEMD_USER_DIR / f"{_unit_basename(app_id)}.service"


def timer_path(app_id: str) -> Path:
    return config.SYSTEMD_USER_DIR / f"{_unit_basename(app_id)}.timer"


def _service_contents(entry: AppEntry) -> str:
    py = config.python_executable()
    return (
        "[Unit]\n"
        f"Description=Griffin Updater - {entry.name}\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        f'ExecStart={py} -m griffin_updater.cli check --id "{entry.id}"\n'
        "\n"
    )


def _timer_contents(entry: AppEntry) -> str:
    oncalendar = entry.schedule.to_oncalendar()
    return (
        "[Unit]\n"
        f"Description=Schedule for Griffin Updater - {entry.name}\n"
        "\n"
        "[Timer]\n"
        f"OnCalendar={oncalendar}\n"
        "Persistent=true\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


def _run_systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", *args], capture_output=True, text=True
    )


def sync_unit(entry: AppEntry) -> tuple[bool, str]:
    """Writes/updates the service+timer for one app and (re)enables it if
    the app is enabled, or disables/removes it otherwise."""
    config.ensure_dirs()
    svc, tmr = service_path(entry.id), timer_path(entry.id)

    if not entry.enabled:
        return remove_unit(entry.id)

    svc.write_text(_service_contents(entry))
    tmr.write_text(_timer_contents(entry))

    reload_res = _run_systemctl("daemon-reload")
    if reload_res.returncode != 0:
        return False, f"daemon-reload failed: {reload_res.stderr.strip()}"

    enable_res = _run_systemctl("enable", "--now", tmr.name)
    if enable_res.returncode != 0:
        return False, f"Could not enable timer: {enable_res.stderr.strip()}"

    return True, f"Scheduled: {entry.schedule.describe()}"


def remove_unit(app_id: str) -> tuple[bool, str]:
    svc, tmr = service_path(app_id), timer_path(app_id)
    _run_systemctl("disable", "--now", tmr.name)
    for p in (svc, tmr):
        p.unlink(missing_ok=True)
    _run_systemctl("daemon-reload")
    return True, "Schedule removed."


def run_now(app_id: str) -> tuple[bool, str]:
    """Fires the oneshot service immediately via systemctl, useful for a
    'Check Now' button that should behave identically to the scheduled run."""
    res = _run_systemctl("start", f"{_unit_basename(app_id)}.service")
    if res.returncode != 0:
        return False, res.stderr.strip()
    return True, "Triggered."


def systemd_available() -> bool:
    import shutil

    return shutil.which("systemctl") is not None
