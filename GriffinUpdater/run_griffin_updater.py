"""Entry point used by PyInstaller / the AppImage (absolute import so the
package's relative imports resolve inside the frozen bundle)."""
import sys

from griffin_updater.main import main

if __name__ == "__main__":
    sys.exit(main())
