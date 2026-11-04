import shutil

import pytest

from shelly import commands  # noqa: F401  (registers commands)
from shelly import platform as plat
from shelly.core import appbook, session


class FakePlatform(plat.Platform):
    """Records what Shelly asked the OS to do, without doing it."""

    key = "windows"

    def __init__(self):
        self.urls, self.apps, self.paths = [], [], []
        self.urls_in, self.revealed = [], []
        self.closed, self.media_actions, self.volumes = [], [], []
        self.trashed = []
        self.error = None

    def _maybe_fail(self):
        if self.error:
            raise plat.PlatformError(self.error)

    def open_url(self, url):
        self._maybe_fail()
        self.urls.append(url)

    def open_url_in(self, app, url):
        self._maybe_fail()
        self.urls_in.append((app, url))

    def open_app(self, name):
        self._maybe_fail()
        self.apps.append(name)

    def close_app(self, name, process=None):
        self._maybe_fail()
        self.closed.append((name, process))

    def open_path(self, path):
        self._maybe_fail()
        self.paths.append(path)

    def reveal(self, path):
        self._maybe_fail()
        self.revealed.append(path)

    def trash(self, path):
        """Pretend-trash: really removes it, so tests see the same result as a real trash."""
        self._maybe_fail()
        self.trashed.append(path)
        shutil.rmtree(path) if path.is_dir() else path.unlink()

    def media(self, action):
        self._maybe_fail()
        self.media_actions.append(action)

    def set_volume(self, percent, music_only):
        self._maybe_fail()
        self.volumes.append((percent, music_only))
        return "music player volume" if music_only else "system volume"


@pytest.fixture
def fake(tmp_path, monkeypatch):
    """A fake OS, the built-in app list only, and a throwaway user apps file."""
    system = FakePlatform()
    plat.set_current(system)
    monkeypatch.setattr(appbook, "USER_FILE", tmp_path / "user" / "apps.toml")
    appbook.set_book(appbook.AppBook.load([appbook.DEFAULT_FILE]))
    yield system
    plat.set_current(None)
    appbook.set_book(None)


@pytest.fixture
def work(tmp_path, monkeypatch, fake):
    """A scratch working folder, plus a fake home folder next to it (and a fake OS)."""
    home = tmp_path / "home"
    home.mkdir()
    folder = tmp_path / "work"
    folder.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.chdir(folder)
    session.clear()
    yield folder
    session.clear()
