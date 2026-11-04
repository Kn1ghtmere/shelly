import subprocess
from pathlib import Path

from .base import Platform, PlatformError

_PLAYERS = ("Spotify", "Music")
_MEDIA = {"play": "play", "pause": "pause", "stop": "pause",
          "next": "next track", "previous": "previous track"}


def _quote(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


class MacPlatform(Platform):
    key = "mac"

    def _osascript(self, script: str) -> None:
        done = subprocess.run(["osascript", "-e", script], capture_output=True)
        if done.returncode != 0:
            raise PlatformError("macOS wouldn't do that.")

    def open_app(self, name: str) -> None:
        done = subprocess.run(["open", "-a", name], capture_output=True)
        if done.returncode != 0:
            raise PlatformError(f"I couldn't start '{name}'. Is it installed?")

    def open_url_in(self, app: str, url: str) -> None:
        done = subprocess.run(["open", "-a", app, url], capture_output=True)
        if done.returncode != 0:
            raise PlatformError(f"I couldn't start '{app}'. Is it installed?")

    def close_app(self, name: str, process: str | None = None) -> None:
        app = Path(name).stem if name.endswith(".app") else name
        done = subprocess.run(
            ["osascript", "-e", f'tell application "{_quote(app)}" to quit'], capture_output=True
        )
        if done.returncode != 0:
            raise PlatformError(f"I couldn't close '{app}'. Is it running?")

    def open_path(self, path: Path) -> None:
        done = subprocess.run(["open", str(path)], capture_output=True)
        if done.returncode != 0:
            raise PlatformError(f"I couldn't open {path}.")

    def reveal(self, path: Path) -> None:
        done = subprocess.run(["open", "-R", str(path)], capture_output=True)
        if done.returncode != 0:
            raise PlatformError(f"I couldn't show {path}.")

    def trash(self, path: Path) -> None:
        script = f'tell application "Finder" to delete POSIX file "{_quote(str(path))}"'
        done = subprocess.run(["osascript", "-e", script], capture_output=True)
        if done.returncode != 0:
            raise PlatformError(f"I couldn't move {path.name} to the Trash.")

    # --- music ---------------------------------------------------------

    def _running_player(self) -> str | None:
        for app in _PLAYERS:
            if subprocess.run(["pgrep", "-x", app], capture_output=True).returncode == 0:
                return app
        return None

    def media(self, action: str) -> None:
        player = self._running_player()
        if player is None:
            raise PlatformError("On a Mac I can control Spotify or Music, but neither is running.")
        self._osascript(f'tell application "{player}" to {_MEDIA[action]}')

    def set_volume(self, percent: int, music_only: bool) -> str:
        player = self._running_player() if music_only else None
        if player:
            self._osascript(f'tell application "{player}" to set sound volume to {percent}')
            return f"{player} volume"
        self._osascript(f"set volume output volume {percent}")
        return "system volume"
