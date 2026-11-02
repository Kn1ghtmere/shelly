import os
from pathlib import Path

import pytest

from shelly.core import paths
from shelly.core.engine import run_line


# --- exit words ----------------------------------------------------------


@pytest.mark.parametrize("word", ["bye", "goodbye", "exit", "quit", "end"])
def test_every_exit_word_exits(word):
    result = run_line(word)
    assert result.ok
    assert result.should_exit
    assert result.message


def test_farewells_differ():
    assert run_line("bye").message != run_line("goodbye").message


# --- goto ----------------------------------------------------------------


@pytest.mark.parametrize("line", ["go to projects", "go projects", "goto projects"])
def test_all_three_ways_to_go(work, line):
    (work / "projects").mkdir()
    assert run_line(line).ok
    assert Path.cwd().samefile(work / "projects")


# --- drives --------------------------------------------------------------


def test_bare_drive_letter_means_the_drive_root():
    assert paths._drive_root("D:") == "D:" + os.sep
    assert paths._drive_root("c:") == "c:" + os.sep


def test_other_text_is_left_alone():
    assert paths._drive_root("D:\\stuff") == "D:\\stuff"
    assert paths._drive_root("ab:") == "ab:"
    assert paths._drive_root("downloads") == "downloads"


# --- make a file ----------------------------------------------------------


def test_make_a_file_with_natural_words(work):
    assert run_line("make a file called notes.txt").ok
    assert (work / "notes.txt").read_text() == ""


def test_make_a_file_with_text(work):
    assert run_line('make file todo.txt with "buy milk"').ok
    assert (work / "todo.txt").read_text() == "buy milk"


def test_touch_and_mkfile_work(work):
    assert run_line("touch a.txt").ok
    assert run_line("mkfile b.txt").ok
    assert (work / "a.txt").exists() and (work / "b.txt").exists()


def test_make_a_file_in_another_folder(work):
    (work / "docs").mkdir()
    assert run_line("make a file called a.txt in docs").ok
    assert (work / "docs" / "a.txt").exists()


def test_make_a_file_never_overwrites(work):
    (work / "a.txt").write_text("keep me")
    result = run_line("make a file called a.txt")
    assert not result.ok
    assert (work / "a.txt").read_text() == "keep me"


def test_make_a_file_in_a_missing_folder_is_refused(work):
    result = run_line("make a file called nope/a.txt")
    assert not result.ok
    assert "can't find the folder" in result.message


def test_make_a_file_with_spaces_needs_quotes(work):
    result = run_line("make a file called my notes.txt")
    assert not result.ok
    assert 'make a file called "my notes.txt"' in result.message
    assert run_line('make a file called "my notes.txt"').ok
    assert (work / "my notes.txt").exists()


def test_make_a_file_without_a_name(work):
    assert not run_line("mkfile").ok


# --- show ----------------------------------------------------------------


def test_show_alone_opens_the_current_folder(work, fake):
    assert run_line("show").ok
    assert fake.paths[0].samefile(work)


def test_show_a_file_highlights_it(work, fake):
    (work / "a.txt").write_text("x")
    assert run_line("show a.txt").ok
    assert fake.revealed[0].samefile(work / "a.txt")
    assert fake.paths == []


def test_show_a_folder_opens_it(work, fake):
    (work / "sub").mkdir()
    assert run_line("show sub").ok
    assert fake.paths[0].samefile(work / "sub")


def test_show_missing_thing(work, fake):
    assert not run_line("show nothing").ok


def test_show_files_is_still_the_terminal_listing(work, fake):
    (work / "a.txt").write_text("x")
    result = run_line("show files")
    assert "a.txt" in result.message
    assert fake.paths == []


def test_show_reports_platform_errors(work, fake):
    fake.error = "No file explorer here."
    assert "No file explorer" in run_line("show").message
