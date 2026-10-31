import shutil
import subprocess
from pathlib import Path

from .base import Platform, PlatformError

_QUIET = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "start_new_session": True}


class LinuxPlatform(Platform):
    key = "linux"

    def open_app(self, name: str) -> None:
        found = shutil.which(name)
        if not found:
            raise PlatformError(f"I couldn't start '{name}'. Is it installed?")
        subprocess.Popen([found], **_QUIET)

    def open_path(self, path: Path) -> None:
        opener = shutil.which("xdg-open")
        if not opener:
            raise PlatformError("I need 'xdg-open' installed to open files here.")
        subprocess.Popen([opener, str(path)], **_QUIET)
