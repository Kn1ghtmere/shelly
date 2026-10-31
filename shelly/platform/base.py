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

    def open_app(self, name: str) -> None:
        raise NotImplementedError

    def open_path(self, path: Path) -> None:
        raise NotImplementedError
