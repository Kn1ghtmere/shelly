from pathlib import Path

from shelly.core import paths


def test_exact_path(work):
    (work / "a.txt").write_text("x")
    assert paths.resolve_existing("a.txt").samefile(work / "a.txt")


def test_ignores_capital_letters(work):
    (work / "Notes.txt").write_text("x")
    assert paths.resolve_existing("notes.txt").samefile(work / "Notes.txt")


def test_up_means_parent(work):
    assert paths.resolve_existing("up").samefile(work.parent)


def test_known_folder_in_home(work):
    downloads = work.parent / "home" / "Downloads"
    downloads.mkdir()
    assert paths.resolve_existing("downloads").samefile(downloads)


def test_real_folder_beats_known_folder(work):
    (work.parent / "home" / "Downloads").mkdir()
    (work / "downloads").mkdir()
    assert paths.resolve_existing("downloads").samefile(work / "downloads")


def test_onedrive_fallback(work):
    desktop = work.parent / "home" / "OneDrive" / "Desktop"
    desktop.mkdir(parents=True)
    assert paths.resolve_existing("desktop").samefile(desktop)


def test_missing_returns_none(work):
    assert paths.resolve_existing("nothing-here") is None


def test_suggests_close_names(work):
    (work / "projects").mkdir()
    assert paths.suggest("projcts") == "projects"
    assert paths.suggest("dowloads") == "downloads"
    assert paths.suggest("zzzzzz") is None


def test_protected_folders(work):
    home = work.parent / "home"
    (home / "Downloads").mkdir()
    assert paths.is_protected(home)
    assert paths.is_protected(home / "Downloads")
    assert paths.is_protected(work)  # the folder you're standing in
    (work / "stuff").mkdir()
    assert not paths.is_protected(work / "stuff")


def test_human_size():
    assert paths.human_size(5) == "5 B"
    assert paths.human_size(2048) == "2.0 KB"
    assert paths.human_size(5 * 1024 * 1024) == "5.0 MB"
