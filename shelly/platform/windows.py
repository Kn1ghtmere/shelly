import ntpath
import os
import shutil
import subprocess
import time
from pathlib import Path

from .base import Platform, PlatformError

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Windows virtual-key codes for the media and volume keys.
_VK_MEDIA = {"play": 0xB3, "pause": 0xB3, "stop": 0xB2, "next": 0xB0, "previous": 0xB1}
_VK_VOLUME_DOWN = 0xAE
_VK_VOLUME_UP = 0xAF


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

    def close_app(self, name: str, process: str | None = None) -> None:
        image = process or _image_name(name)
        done = subprocess.run(
            ["taskkill", "/IM", image], capture_output=True, text=True, creationflags=_NO_WINDOW
        )
        if done.returncode != 0:
            raise PlatformError(f"I don't see {image} running.")

    def open_path(self, path: Path) -> None:
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except OSError as error:
            raise PlatformError(f"I couldn't open {path}: {error}") from error

    def reveal(self, path: Path) -> None:
        # explorer reports exit code 1 even when it works, so don't check it.
        subprocess.Popen(f'explorer /select,"{path}"')

    def trash(self, path: Path) -> None:
        method = "DeleteDirectory" if path.is_dir() else "DeleteFile"
        script = (
            "Add-Type -AssemblyName Microsoft.VisualBasic; "
            f"[Microsoft.VisualBasic.FileIO.FileSystem]::{method}"
            "($env:SHELLY_TRASH, 'OnlyErrorDialogs', 'SendToRecycleBin')"
        )
        done = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            env={**os.environ, "SHELLY_TRASH": str(path)},
            capture_output=True, text=True, creationflags=_NO_WINDOW,
        )
        if done.returncode != 0:
            raise PlatformError(f"I couldn't move {path.name} to the Recycle Bin.")

    # --- music ---------------------------------------------------------

    def _press(self, key_code: int, times: int = 1) -> None:
        import ctypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        for _ in range(times):
            user32.keybd_event(key_code, 0, 0, 0)  # key down
            user32.keybd_event(key_code, 0, 2, 0)  # key up
            time.sleep(0.003)

    def media(self, action: str) -> None:
        # Play and pause are one key on Windows: it flips between them.
        self._press(_VK_MEDIA[action])

    def set_volume(self, percent: int, music_only: bool) -> str:
        # Windows has no built-in way to set volume directly, but each volume
        # key press moves it 2%. So: all the way down, then up to the target.
        self._press(_VK_VOLUME_DOWN, 50)
        self._press(_VK_VOLUME_UP, round(percent / 2))
        return "system volume"


def _image_name(name: str) -> str:
    base = ntpath.basename(name)
    return base if base.lower().endswith(".exe") else base + ".exe"


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
