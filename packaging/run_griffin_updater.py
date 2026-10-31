"""Entry point used only for PyInstaller bundling. Importing the package
normally (instead of pointing PyInstaller at griffin_updater/main.py
directly) keeps the package's relative imports (`from . import config`)
working, since main.py then runs as `griffin_updater.main`, not as a
top-level `__main__` script."""
import sys

from griffin_updater.main import main

if __name__ == "__main__":
    sys.exit(main())
