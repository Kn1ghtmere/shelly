import subprocess
from pathlib import Path

from .base import Platform, PlatformError


class MacPlatform(Platform):
    key = "mac"

    def open_app(self, name: str) -> None:
        done = subprocess.run(["open", "-a", name], capture_output=True)
        if done.returncode != 0:
            raise PlatformError(f"I couldn't start '{name}'. Is it installed?")

    def open_url_in(self, app: str, url: str) -> None:
        done = subprocess.run(["open", "-a", app, url], capture_output=True)
        if done.returncode != 0:
            raise PlatformError(f"I couldn't start '{app}'. Is it installed?")

    def open_path(self, path: Path) -> None:
        done = subprocess.run(["open", str(path)], capture_output=True)
        if done.returncode != 0:
            raise PlatformError(f"I couldn't open {path}.")

    def reveal(self, path: Path) -> None:
        done = subprocess.run(["open", "-R", str(path)], capture_output=True)
        if done.returncode != 0:
            raise PlatformError(f"I couldn't show {path}.")
