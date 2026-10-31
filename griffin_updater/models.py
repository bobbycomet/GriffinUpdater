from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from . import config

VALID_CATEGORIES = ("deb", "appimage", "archive")
VALID_SOURCE_TYPES = ("static_url", "github_release")
VALID_FREQUENCIES = ("daily", "weekly", "monthly", "custom")

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


@dataclass
class Schedule:
    frequency: str = "weekly"       # daily | weekly | monthly | custom
    time: str = "13:00"             # HH:MM, 24h
    day_of_week: str = "Sun"        # used when frequency == weekly (Mon..Sun)
    day_of_month: int = 1           # used when frequency == monthly (1-28 kept safe)
    custom_oncalendar: str = ""     # raw systemd OnCalendar= expression, used when frequency == custom

    def to_oncalendar(self) -> str:
        hh, mm = (self.time.split(":") + ["00"])[:2]
        hh = hh.zfill(2)
        mm = mm.zfill(2)
        if self.frequency == "daily":
            return f"*-*-* {hh}:{mm}:00"
        if self.frequency == "weekly":
            day = self.day_of_week if self.day_of_week in WEEKDAYS else "Sun"
            return f"{day} *-*-* {hh}:{mm}:00"
        if self.frequency == "monthly":
            dom = max(1, min(28, int(self.day_of_month or 1)))
            return f"*-*-{dom:02d} {hh}:{mm}:00"
        if self.frequency == "custom" and self.custom_oncalendar.strip():
            return self.custom_oncalendar.strip()
        # sensible fallback
        return f"*-*-* {hh}:{mm}:00"

    def describe(self) -> str:
        if self.frequency == "daily":
            return f"Daily at {self.time}"
        if self.frequency == "weekly":
            return f"Weekly on {self.day_of_week} at {self.time}"
        if self.frequency == "monthly":
            return f"Monthly on day {self.day_of_month} at {self.time}"
        if self.frequency == "custom":
            return f"Custom: {self.custom_oncalendar or '(not set)'}"
        return "Unscheduled"


@dataclass
class AppEntry:
    id: str
    name: str
    category: str = "deb"                 # deb | appimage
    source_type: str = "static_url"       # static_url | github_release
    description: str = ""
    icon: str = ""

    # static_url mode
    url: str = ""
    version_regex: str = ""               # optional override; default extracts N.N.N-like token

    # github_release mode
    github_owner: str = ""
    github_repo: str = ""
    asset_pattern: str = ""               # regex matched against release asset filenames

    # deb-specific
    package_name: str = ""                # dpkg package name, defaults to id if blank

    # optional integrity check, applies to both deb and appimage downloads
    sha256: str = ""                      # expected hex digest; blank = not verified

    # appimage-specific
    appimage_target_dir: str = str(config.DESKTOP_DIR)
    appimage_filename: str = ""           # optional forced filename; blank = keep downloaded name
    delete_old_appimage: bool = True

    # archive-specific (zip/tar.xz that gets extracted into a folder, e.g. Godot)
    archive_install_dir: str = str(config.HOME / "Applications")
    archive_subdir_name: str = ""         # folder name under archive_install_dir; blank = use id
    archive_executable_pattern: str = ""  # regex matched against extracted filenames to find the binary
    archive_delete_old: bool = True       # wipe the subdir before extracting the new version
    archive_symlink_name: str = ""        # optional stable-named symlink under archive_install_dir

    enabled: bool = True
    notify: bool = True
    schedule: Schedule = field(default_factory=Schedule)

    from_catalog: bool = False            # true if it originated from the shared apps.json

    def effective_package_name(self) -> str:
        return self.package_name.strip() or self.id

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "AppEntry":
        sched_d = d.get("schedule") or {}
        schedule = Schedule(
            frequency=sched_d.get("frequency", "weekly"),
            time=sched_d.get("time", "13:00"),
            day_of_week=sched_d.get("day_of_week", "Sun"),
            day_of_month=sched_d.get("day_of_month", 1),
            custom_oncalendar=sched_d.get("custom_oncalendar", ""),
        )
        known = {f for f in AppEntry.__dataclass_fields__.keys()}
        clean = {k: v for k, v in d.items() if k in known and k != "schedule"}
        return AppEntry(schedule=schedule, **clean)


def load_apps() -> list[AppEntry]:
    if not config.MY_APPS_FILE.exists():
        return []
    try:
        raw = json.loads(config.MY_APPS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return [AppEntry.from_dict(item) for item in raw.get("apps", [])]


def save_apps(apps: list[AppEntry]) -> None:
    config.ensure_dirs()
    payload = {"apps": [a.to_dict() for a in apps]}
    config.MY_APPS_FILE.write_text(json.dumps(payload, indent=2))


def upsert_app(apps: list[AppEntry], entry: AppEntry) -> list[AppEntry]:
    out = [a for a in apps if a.id != entry.id]
    out.append(entry)
    return out


def remove_app(apps: list[AppEntry], app_id: str) -> list[AppEntry]:
    return [a for a in apps if a.id != app_id]
