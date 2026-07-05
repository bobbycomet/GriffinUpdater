from __future__ import annotations

from dataclasses import dataclass

from ..models import AppEntry
from . import state as state_mod
from . import deb_installer, appimage_installer
from .version import resolve, VersionResolutionError
from .notifier import notify


@dataclass
class CheckResult:
    app_id: str
    ok: bool
    updated: bool
    message: str


def check_and_update(entry: AppEntry) -> CheckResult:
    try:
        resolved = resolve(entry)
    except VersionResolutionError as exc:
        msg = f"Check failed: {exc}"
        state_mod.append_log(entry.id, msg)
        return CheckResult(entry.id, ok=False, updated=False, message=msg)

    try:
        if entry.category == "deb":
            did_install, message = deb_installer.check_and_install(entry, resolved)
            if did_install:
                state_mod.update_app_state(entry.id, installed_version=resolved.version)
        else:
            st = state_mod.get_app_state(entry.id)
            did_install, message, new_path = appimage_installer.check_and_install(
                entry, resolved, st.get("installed_version"), st.get("installed_path", "")
            )
            if did_install:
                state_mod.update_app_state(
                    entry.id, installed_version=resolved.version, installed_path=new_path
                )
    except (deb_installer.DebInstallError, appimage_installer.AppImageInstallError) as exc:
        msg = f"Update failed: {exc}"
        state_mod.append_log(entry.id, msg)
        if entry.notify:
            notify("Griffin Updater - Error", f"{entry.name}: {exc}")
        return CheckResult(entry.id, ok=False, updated=False, message=msg)

    state_mod.append_log(entry.id, message)
    if did_install and entry.notify:
        notify("Griffin Updater", message)

    return CheckResult(entry.id, ok=True, updated=did_install, message=message)
