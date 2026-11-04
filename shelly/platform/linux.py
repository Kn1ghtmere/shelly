import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from .base import Platform, PlatformError

_QUIET = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "start_new_session": True}
_MEDIA = {"play": "play", "pause": "pause", "stop": "pause", "next": "next", "previous": "previous"}


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

    def close_app(self, name: str, process: str | None = None) -> None:
        pkill = shutil.which("pkill")
        if not pkill:
            raise PlatformError("I need 'pkill' to close programs here.")
        target = process or Path(name).name
        done = subprocess.run([pkill, "-x", target], capture_output=True)
        if done.returncode != 0:
            raise PlatformError(f"I don't see {target} running.")

    def open_path(self, path: Path) -> None:
        opener = shutil.which("xdg-open")
        if not opener:
            raise PlatformError("I need 'xdg-open' installed to open files here.")
        subprocess.Popen([opener, str(path)], **_QUIET)

    # reveal(): Linux file managers can't be told to highlight a file portably,
    # so the base class opens the containing folder.

    def trash(self, path: Path) -> None:
        gio = shutil.which("gio")
        if gio and subprocess.run([gio, "trash", str(path)], capture_output=True).returncode == 0:
            return
        _freedesktop_trash(path)

    # --- music ---------------------------------------------------------

    def media(self, action: str) -> None:
        playerctl = shutil.which("playerctl")
        if not playerctl:
            raise PlatformError(
                "I need 'playerctl' installed to control music here (for example: sudo apt install playerctl)."
            )
        done = subprocess.run([playerctl, _MEDIA[action]], capture_output=True)
        if done.returncode != 0:
            raise PlatformError("I couldn't find a music player to control.")

    def set_volume(self, percent: int, music_only: bool) -> str:
        playerctl = shutil.which("playerctl")
        if music_only and playerctl:
            done = subprocess.run([playerctl, "volume", f"{percent / 100:.2f}"], capture_output=True)
            if done.returncode == 0:
                return "music player volume"
        pactl = shutil.which("pactl")
        if pactl:
            subprocess.run([pactl, "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"], capture_output=True)
            return "system volume"
        amixer = shutil.which("amixer")
        if amixer:
            subprocess.run([amixer, "sset", "Master", f"{percent}%"], capture_output=True)
            return "system volume"
        raise PlatformError("I couldn't find a way to set the volume here (tried playerctl, pactl, amixer).")


def _freedesktop_trash(path: Path) -> None:
    """The standard Linux trash folder, for when `gio` isn't there."""
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    files, info = data / "Trash" / "files", data / "Trash" / "info"
    files.mkdir(parents=True, exist_ok=True)
    info.mkdir(parents=True, exist_ok=True)

    name, number = path.name, 1
    while (files / name).exists() or (info / f"{name}.trashinfo").exists():
        number += 1
        name = f"{path.stem} ({number}){path.suffix}"

    record = info / f"{name}.trashinfo"
    record.write_text(
        "[Trash Info]\n"
        f"Path={quote(str(path.resolve()))}\n"
        f"DeletionDate={datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n"
    )
    try:
        shutil.move(str(path), str(files / name))
    except OSError as error:
        record.unlink(missing_ok=True)
        raise PlatformError(f"I couldn't move {path.name} to the trash: {error}") from error
