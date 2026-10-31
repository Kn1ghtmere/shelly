import os
import shutil
import subprocess
from pathlib import Path

from .base import Platform, PlatformError


class WindowsPlatform(Platform):
    key = "windows"

    def open_app(self, name: str) -> None:
        try:
            os.startfile(name)  # type: ignore[attr-defined]
            return
        except OSError:
            pass
        found = shutil.which(name)
        if not found:
            raise PlatformError(f"I couldn't start '{name}'. Is it installed?")
        subprocess.Popen([found])

    def open_path(self, path: Path) -> None:
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except OSError as error:
            raise PlatformError(f"I couldn't open {path}: {error}") from error
