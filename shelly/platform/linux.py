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

    def open_url_in(self, app: str, url: str) -> None:
        found = shutil.which(app)
        if not found:
            raise PlatformError(f"I couldn't start '{app}'. Is it installed?")
        subprocess.Popen([found, url], **_QUIET)

    def open_path(self, path: Path) -> None:
        opener = shutil.which("xdg-open")
        if not opener:
            raise PlatformError("I need 'xdg-open' installed to open files here.")
        subprocess.Popen([opener, str(path)], **_QUIET)

    # reveal(): Linux file managers can't be told to highlight a file portably,
    # so the base class opens the containing folder.
