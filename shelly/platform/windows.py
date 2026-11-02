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

    def open_url_in(self, app: str, url: str) -> None:
        exe = _find_exe(app)
        if exe is None:
            raise PlatformError(f"I couldn't find '{app}'. Is it installed?")
        subprocess.Popen([exe, url])

    def open_path(self, path: Path) -> None:
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except OSError as error:
            raise PlatformError(f"I couldn't open {path}: {error}") from error

    def reveal(self, path: Path) -> None:
        # explorer reports exit code 1 even when it works, so don't check it.
        subprocess.Popen(f'explorer /select,"{path}"')


def _find_exe(name: str) -> str | None:
    """Find a program's .exe: a full path, something on PATH, or Windows' App Paths list."""
    if os.path.isfile(name):
        return name
    found = shutil.which(name)
    if found:
        return found
    try:
        import winreg
    except ImportError:
        return None
    exe = name if name.lower().endswith(".exe") else name + ".exe"
    key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "")
        except OSError:
            continue
        value = str(value).strip('"')
        if os.path.isfile(value):
            return value
    return None
