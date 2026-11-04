import webbrowser
from pathlib import Path


class PlatformError(Exception):
    """Something the operating system couldn't do. The message is for humans."""


class Platform:
    """What Shelly needs from an operating system. One subclass per OS.

    Commands never check which OS they're on. They call these methods and
    the right subclass does the OS-specific part.
    """

    key = "linux"  # used to pick the right app name from apps.toml

    def open_url(self, url: str) -> None:
        if not webbrowser.open(url):
            raise PlatformError("I couldn't open a web browser.")

    def open_url_in(self, app: str, url: str) -> None:
        """Open a web address in one specific browser."""
        raise NotImplementedError

    def open_app(self, name: str) -> None:
        raise NotImplementedError

    def close_app(self, name: str, process: str | None = None) -> None:
        """Politely ask a program to close (it may still ask about unsaved work)."""
        raise NotImplementedError

    def open_path(self, path: Path) -> None:
        raise NotImplementedError

    def reveal(self, path: Path) -> None:
        """Show a file in the file explorer (highlighted where the OS can)."""
        self.open_path(path.parent)

    def trash(self, path: Path) -> None:
        """Move a file or folder to the trash / Recycle Bin."""
        raise NotImplementedError

    def media(self, action: str) -> None:
        """action: play, pause, stop, next or previous."""
        raise NotImplementedError

    def set_volume(self, percent: int, music_only: bool) -> str:
        """Set the volume. Returns what was changed, like 'system volume'."""
        raise NotImplementedError
