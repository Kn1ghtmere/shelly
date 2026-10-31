import pytest

from shelly import commands  # noqa: F401  (registers commands)
from shelly.core import session


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
