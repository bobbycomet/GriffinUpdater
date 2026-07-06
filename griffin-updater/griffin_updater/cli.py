from __future__ import annotations

import argparse
import sys

from . import config
from .models import load_apps
from .core.checker import check_and_update


def cmd_check(app_id: str) -> int:
    apps = load_apps()
    matches = [a for a in apps if a.id == app_id]
    if not matches:
        print(f"No such app id: {app_id}", file=sys.stderr)
        return 1
    entry = matches[0]
    if not entry.enabled:
        print(f"{entry.name} is disabled, skipping.")
        return 0
    result = check_and_update(entry)
    print(result.message)
    return 0 if result.ok else 2


def cmd_check_all() -> int:
    apps = [a for a in load_apps() if a.enabled]
    if not apps:
        print("No enabled apps configured.")
        return 0
    exit_code = 0
    for entry in apps:
        result = check_and_update(entry)
        print(f"[{entry.name}] {result.message}")
        if not result.ok:
            exit_code = 2
    return exit_code


def cmd_install_timers() -> int:
    from .core import systemd_manager

    if not systemd_manager.systemd_available():
        print("systemctl not found on this system.", file=sys.stderr)
        return 1
    apps = load_apps()
    for entry in apps:
        ok, msg = systemd_manager.sync_unit(entry)
        print(f"[{entry.name}] {'OK' if ok else 'FAILED'}: {msg}")
    return 0


def main() -> int:
    config.ensure_dirs()
    parser = argparse.ArgumentParser(prog="griffin-updater", description="Griffin Updater CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Check and update a single app")
    p_check.add_argument("--id", required=True, dest="app_id")

    sub.add_parser("check-all", help="Check and update every enabled app")
    sub.add_parser("install-timers", help="(Re)generate systemd --user units for all apps")

    args = parser.parse_args()

    if args.command == "check":
        return cmd_check(args.app_id)
    if args.command == "check-all":
        return cmd_check_all()
    if args.command == "install-timers":
        return cmd_install_timers()

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
