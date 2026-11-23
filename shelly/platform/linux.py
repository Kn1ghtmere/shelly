import os
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from .base import InstalledApp, Platform, PlatformError

_QUIET = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "start_new_session": True}
_MEDIA = {"play": "play", "pause": "pause", "stop": "pause", "next": "next", "previous": "previous"}


class LinuxPlatform(Platform):
    key = "linux"

    def detect_apps(self) -> list[InstalledApp]:
        apps: dict[str, InstalledApp] = {}
        for directory in _application_dirs():
            if not directory.is_dir():
                continue
            for entry in directory.rglob("*.desktop"):
                name, executable = _desktop_app(entry)
                if not name or not executable:
                    continue
                found = shutil.which(executable)
                if found:
                    path = Path(found)
                    key = os.path.normcase(os.path.normpath(str(path)))
                    apps.setdefault(key, InstalledApp(name, path))
        return sorted(apps.values(), key=lambda app: (app.name.casefold(), str(app.path).casefold()))

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


def _application_dirs() -> list[Path]:
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    directories = [data_home / "applications"]
    directories.extend(Path(root) / "applications" for root in data_dirs.split(os.pathsep) if root)
    directories.extend([
        Path("/var/lib/flatpak/exports/share/applications"),
        Path("/var/lib/snapd/desktop/applications"),
    ])
    return directories


def _desktop_app(entry: Path) -> tuple[str | None, str | None]:
    try:
        lines = entry.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise PlatformError(f"I couldn't read the app menu entry {entry}: {error}") from error

    values: dict[str, str] = {}
    in_desktop_entry = False
    for line in lines:
        line = line.strip()
        if line.startswith("["):
            in_desktop_entry = line == "[Desktop Entry]"
        elif in_desktop_entry and line and not line.startswith("#"):
            key, separator, value = line.partition("=")
            if separator:
                values[key] = value

    if (
        values.get("Type", "Application") != "Application"
        or values.get("Hidden", "").lower() == "true"
        or values.get("NoDisplay", "").lower() == "true"
    ):
        return None, None

    command = values.get("Exec", "")
    try:
        tokens = shlex.split(command)
    except ValueError as error:
        raise PlatformError(f"I couldn't parse the launch command in {entry}: {error}") from error
    if not tokens:
        return None, None

    if Path(tokens[0]).name == "env":
        tokens = tokens[1:]
        while tokens and ("=" in tokens[0] or tokens[0].startswith("-")):
            if tokens[0] == "-u" and len(tokens) > 1:
                tokens = tokens[2:]
            else:
                tokens = tokens[1:]
    if not tokens or Path(tokens[0]).name in {"sh", "bash", "dash", "zsh"}:
        return None, None
    return values.get("Name") or entry.stem, tokens[0]


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
