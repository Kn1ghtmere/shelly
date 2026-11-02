import subprocess
from pathlib import Path

import pytest

from shelly.platform import linux, mac, windows
from shelly.platform.base import PlatformError


class Runner:
    """Stands in for subprocess.run: records commands, returns a chosen exit code."""

    def __init__(self, code=lambda cmd: 0):
        self.calls, self.code = [], code

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        return subprocess.CompletedProcess(cmd, self.code(cmd), "", "")


# --- Windows ---------------------------------------------------------------------------------------


@pytest.fixture
def win(monkeypatch):
    system = windows.WindowsPlatform()
    system.pressed = []
    monkeypatch.setattr(system, "_press", lambda code, times=1: system.pressed.append((code, times)))
    return system


def test_windows_media_keys(win):
    for action, key in [("play", 0xB3), ("pause", 0xB3), ("next", 0xB0), ("previous", 0xB1), ("stop", 0xB2)]:
        win.pressed.clear()
        win.media(action)
        assert win.pressed == [(key, 1)]


def test_windows_volume_goes_to_zero_then_up(win):
    assert win.set_volume(50, music_only=True) == "system volume"
    assert win.pressed == [(0xAE, 50), (0xAF, 25)]
    win.pressed.clear()
    win.set_volume(15, False)
    assert win.pressed == [(0xAE, 50), (0xAF, 8)]


def test_windows_close_uses_taskkill(monkeypatch):
    run = Runner()
    monkeypatch.setattr(windows.subprocess, "run", run)
    system = windows.WindowsPlatform()
    system.close_app("notepad")
    system.close_app(r"C:\Program Files\Brave\brave.exe")
    system.close_app("calc", "CalculatorApp.exe")
    assert [c[2] for c in run.calls] == ["notepad.exe", "brave.exe", "CalculatorApp.exe"]
    assert run.calls[0][:2] == ["taskkill", "/IM"]
    assert "/F" not in run.calls[0]  # politely, not by force


def test_windows_close_when_not_running(monkeypatch):
    monkeypatch.setattr(windows.subprocess, "run", Runner(lambda cmd: 128))
    with pytest.raises(PlatformError, match="notepad.exe"):
        windows.WindowsPlatform().close_app("notepad")


def test_windows_trash_uses_the_recycle_bin(monkeypatch, tmp_path):
    run = Runner()
    monkeypatch.setattr(windows.subprocess, "run", run)
    folder = tmp_path / "d"
    folder.mkdir()
    windows.WindowsPlatform().trash(folder)
    assert "SendToRecycleBin" in run.calls[0][-1] and "DeleteDirectory" in run.calls[0][-1]


def test_windows_trash_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(windows.subprocess, "run", Runner(lambda cmd: 1))
    f = tmp_path / "f.txt"
    f.write_text("x")
    with pytest.raises(PlatformError, match="Recycle Bin"):
        windows.WindowsPlatform().trash(f)


def test_image_names():
    assert windows._image_name("notepad") == "notepad.exe"
    assert windows._image_name(r"C:\x\Brave.exe") == "Brave.exe"


# --- macOS --------------------------------------------------------------------------------------------


def test_mac_media_needs_a_running_player(monkeypatch):
    monkeypatch.setattr(mac.subprocess, "run", Runner(lambda cmd: 1))
    with pytest.raises(PlatformError, match="Spotify or Music"):
        mac.MacPlatform().media("play")


def test_mac_media_talks_to_spotify(monkeypatch):
    run = Runner(lambda cmd: 1 if cmd[0] == "pgrep" and cmd[2] != "Spotify" else 0)
    monkeypatch.setattr(mac.subprocess, "run", run)
    mac.MacPlatform().media("next")
    assert run.calls[-1] == ["osascript", "-e", 'tell application "Spotify" to next track']


def test_mac_music_volume_targets_the_player(monkeypatch):
    run = Runner()
    monkeypatch.setattr(mac.subprocess, "run", run)
    assert mac.MacPlatform().set_volume(30, music_only=True) == "Spotify volume"
    assert "set sound volume to 30" in run.calls[-1][-1]


def test_mac_system_volume(monkeypatch):
    run = Runner()
    monkeypatch.setattr(mac.subprocess, "run", run)
    assert mac.MacPlatform().set_volume(30, music_only=False) == "system volume"
    assert run.calls[-1][-1] == "set volume output volume 30"


def test_mac_close_and_trash(monkeypatch):
    run = Runner()
    monkeypatch.setattr(mac.subprocess, "run", run)
    system = mac.MacPlatform()
    system.close_app("/Applications/Brave Browser.app")
    assert run.calls[-1][-1] == 'tell application "Brave Browser" to quit'
    system.trash(Path('/tmp/a "b".txt'))
    assert r'POSIX file "/tmp/a \"b\".txt"' in run.calls[-1][-1]


# --- Linux ----------------------------------------------------------------------------------------------


def test_linux_media_with_playerctl(monkeypatch):
    run = Runner()
    monkeypatch.setattr(linux.subprocess, "run", run)
    monkeypatch.setattr(linux.shutil, "which", lambda name: f"/usr/bin/{name}")
    for action, word in [("play", "play"), ("pause", "pause"), ("stop", "pause"),
                         ("next", "next"), ("previous", "previous")]:
        linux.LinuxPlatform().media(action)
        assert run.calls[-1] == ["/usr/bin/playerctl", word]


def test_linux_media_without_playerctl(monkeypatch):
    monkeypatch.setattr(linux.shutil, "which", lambda name: None)
    with pytest.raises(PlatformError, match="playerctl"):
        linux.LinuxPlatform().media("play")


def test_linux_music_volume_prefers_the_player(monkeypatch):
    run = Runner()
    monkeypatch.setattr(linux.subprocess, "run", run)
    monkeypatch.setattr(linux.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert linux.LinuxPlatform().set_volume(30, music_only=True) == "music player volume"
    assert run.calls[-1] == ["/usr/bin/playerctl", "volume", "0.30"]


def test_linux_system_volume_falls_back(monkeypatch):
    run = Runner()
    monkeypatch.setattr(linux.subprocess, "run", run)
    monkeypatch.setattr(linux.shutil, "which", lambda name: "/usr/bin/pactl" if name == "pactl" else None)
    assert linux.LinuxPlatform().set_volume(30, music_only=True) == "system volume"
    assert run.calls[-1][1:] == ["set-sink-volume", "@DEFAULT_SINK@", "30%"]


def test_linux_volume_with_no_tools(monkeypatch):
    monkeypatch.setattr(linux.shutil, "which", lambda name: None)
    with pytest.raises(PlatformError, match="volume"):
        linux.LinuxPlatform().set_volume(30, False)


def test_linux_close(monkeypatch):
    run = Runner()
    monkeypatch.setattr(linux.subprocess, "run", run)
    monkeypatch.setattr(linux.shutil, "which", lambda name: f"/usr/bin/{name}")
    linux.LinuxPlatform().close_app("/usr/bin/gedit")
    assert run.calls[-1] == ["/usr/bin/pkill", "-x", "gedit"]


def test_linux_close_not_running(monkeypatch):
    monkeypatch.setattr(linux.subprocess, "run", Runner(lambda cmd: 1))
    monkeypatch.setattr(linux.shutil, "which", lambda name: f"/usr/bin/{name}")
    with pytest.raises(PlatformError, match="running"):
        linux.LinuxPlatform().close_app("gedit")


@pytest.fixture
def no_gio(monkeypatch, tmp_path):
    monkeypatch.setattr(linux.shutil, "which", lambda name: None)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    return tmp_path / "share" / "Trash"


def test_linux_trash_follows_the_freedesktop_standard(no_gio, tmp_path):
    f = tmp_path / "old file.txt"
    f.write_text("bye")
    linux.LinuxPlatform().trash(f)
    assert not f.exists()
    assert (no_gio / "files" / "old file.txt").read_text() == "bye"
    info = (no_gio / "info" / "old file.txt.trashinfo").read_text()
    assert info.startswith("[Trash Info]\nPath=") and "old%20file.txt" in info and "DeletionDate=" in info


def test_linux_trash_handles_name_clashes_and_folders(no_gio, tmp_path):
    system = linux.LinuxPlatform()
    for _ in range(2):
        f = tmp_path / "a.txt"
        f.write_text("x")
        system.trash(f)
    folder = tmp_path / "d"
    (folder / "inner").mkdir(parents=True)
    system.trash(folder)
    names = sorted(p.name for p in (no_gio / "files").iterdir())
    assert names == ["a (2).txt", "a.txt", "d"]


def test_linux_trash_prefers_gio(monkeypatch, tmp_path):
    run = Runner()
    monkeypatch.setattr(linux.subprocess, "run", run)
    monkeypatch.setattr(linux.shutil, "which", lambda name: "/usr/bin/gio")
    f = tmp_path / "a.txt"
    f.write_text("x")
    linux.LinuxPlatform().trash(f)
    assert run.calls == [["/usr/bin/gio", "trash", str(f)]]
    assert f.exists()  # gio (not us) does the moving
