from __future__ import annotations

import json
import time
from typing import Any

from .. import config

MAX_LOG_ENTRIES_PER_APP = 50


def _load() -> dict[str, Any]:
    if not config.STATE_FILE.exists():
        return {"apps": {}}
    try:
        return json.loads(config.STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"apps": {}}


def _save(data: dict[str, Any]) -> None:
    config.ensure_dirs()
    config.STATE_FILE.write_text(json.dumps(data, indent=2))


def get_app_state(app_id: str) -> dict[str, Any]:
    data = _load()
    return data.get("apps", {}).get(app_id, {
        "installed_version": None,
        "installed_path": "",
        "last_checked": None,
        "last_result": "never checked",
        "log": [],
    })


def update_app_state(app_id: str, **fields: Any) -> None:
    data = _load()
    apps = data.setdefault("apps", {})
    entry = apps.setdefault(app_id, {
        "installed_version": None,
        "installed_path": "",
        "last_checked": None,
        "last_result": "never checked",
        "log": [],
    })
    entry.update(fields)
    _save(data)


def append_log(app_id: str, message: str) -> None:
    data = _load()
    apps = data.setdefault("apps", {})
    entry = apps.setdefault(app_id, {
        "installed_version": None,
        "installed_path": "",
        "last_checked": None,
        "last_result": "never checked",
        "log": [],
    })
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    log = entry.setdefault("log", [])
    log.append(f"[{ts}] {message}")
    entry["log"] = log[-MAX_LOG_ENTRIES_PER_APP:]
    entry["last_checked"] = ts
    entry["last_result"] = message
    apps[app_id] = entry
    _save(data)

    # also mirror to the flat rolling log file for easy tailing
    config.ensure_dirs()
    with open(config.LOG_FILE, "a") as f:
        f.write(f"[{ts}] [{app_id}] {message}\n")
