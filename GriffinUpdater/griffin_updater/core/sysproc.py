"""
Helpers for launching host programs (dpkg, apt-get, pkexec, systemctl,
notify-send) from a frozen/AppImage build.

PyInstaller prepends its bundle directory to LD_LIBRARY_PATH (and saves the
original value in LD_LIBRARY_PATH_ORIG). Host tools launched with that
variable would load our bundled libz/libstdc++/etc. instead of their own and
can crash or misbehave, so child processes get the original environment back.
"""
from __future__ import annotations

import os
import sys


def host_env() -> dict[str, str]:
    env = dict(os.environ)
    orig = env.pop("LD_LIBRARY_PATH_ORIG", None)
    if orig is not None:
        env["LD_LIBRARY_PATH"] = orig
    elif getattr(sys, "frozen", False):
        env.pop("LD_LIBRARY_PATH", None)
    return env
