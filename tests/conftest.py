import pytest

from shelly import commands  # noqa: F401  (registers commands)
from shelly import platform as plat
from shelly.core import appbook, session


@pytest.fixture
def work(tmp_path, monkeypatch):
    """A scratch working folder, plus a fake home folder next to it."""
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


class FakePlatform(plat.Platform):
    """Records what Shelly asked the OS to do, without doing it."""

    key = "windows"

    def __init__(self):
        self.urls, self.apps, self.paths = [], [], []
        self.urls_in, self.revealed = [], []
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

    def open_path(self, path):
        self._maybe_fail()
        self.paths.append(path)

    def reveal(self, path):
        self._maybe_fail()
        self.revealed.append(path)


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
