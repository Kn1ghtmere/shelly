import os
from pathlib import Path

import pytest

from shelly.core.engine import answer, run_line
from shelly.ui import completion


def add_browser(tmp_path, name="brave"):
    exe = tmp_path / f"{name}.exe"
    exe.write_text("x")
    result = run_line(f'add app "{exe}" as {name}')
    answer(answer(result.ask, "1").ask, "none")
    return exe


# --- open in / using a browser -----------------------------------------------------------------


def test_open_a_site_in_a_browser(fake):
    assert run_line("open youtube in chrome").ok
    assert fake.urls_in == [("chrome", "https://www.youtube.com")]
    assert fake.urls == []


def test_using_means_the_same(fake):
    assert run_line("open youtube using chrome").ok
    assert fake.urls_in == [("chrome", "https://www.youtube.com")]


def test_search_in_a_chosen_browser(fake):
    run_line('open youtube search "ben 10" using edge')
    assert fake.urls_in == [("msedge", "https://www.youtube.com/results?search_query=ben+10")]


def test_the_browsers_name_depends_on_the_os(fake):
    fake.key = "mac"
    run_line("open youtube using chrome")
    assert fake.urls_in[0][0] == "Google Chrome"


def test_message_says_which_browser(fake):
    assert "(in chrome)" in run_line("open youtube using chrome").message


def test_a_browser_you_added_works_too(fake, tmp_path):
    exe = add_browser(tmp_path)
    answer(run_line("add website https://rythm.fm as rythm").ask, "no")
    assert run_line("open rythm using brave").ok
    assert fake.urls_in == [(str(exe.resolve()), "https://rythm.fm")]


def test_using_something_that_is_not_a_browser(fake):
    result = run_line("open youtube using notepad")
    assert not result.ok and "isn't a browser" in result.message


def test_using_an_unknown_browser_suggests(fake):
    result = run_line("open youtube using crome")
    assert not result.ok and "chrome" in result.message


def test_a_program_cannot_open_inside_a_browser(fake):
    result = run_line("open firefox in chrome")
    assert not result.ok and "not a website" in result.message


def test_in_something_that_is_not_a_browser_is_a_place(fake):
    result = run_line("open youtube in downloads")
    assert not result.ok and "using <browser>" in result.message


def test_open_a_link_directly(fake):
    assert run_line('open "https://example.com"').ok
    assert fake.urls == ["https://example.com"]
    assert run_line('open "https://example.com" in chrome').ok
    assert fake.urls_in == [("chrome", "https://example.com")]


def test_open_a_file_in_a_place(work, fake):
    (work / "docs").mkdir()
    (work / "docs" / "n.txt").write_text("x")
    assert run_line("open n.txt in docs").ok
    assert fake.paths[0].samefile(work / "docs" / "n.txt")
    assert not run_line("open n.txt in nope").ok


# --- close ---------------------------------------------------------------------------------------------


def test_close_a_program(fake):
    assert run_line("close notepad").ok
    assert fake.closed == [("notepad", "notepad.exe")]


def test_close_uses_the_odd_process_name(fake):
    run_line("close calc")
    assert fake.closed == [("calc", "CalculatorApp.exe")]


def test_close_several(fake):
    run_line("close chrome and notepad")
    assert [c[0] for c in fake.closed] == ["chrome", "notepad"]


def test_process_names_are_windows_only(fake):
    fake.key = "mac"
    run_line("close notepad")
    assert fake.closed == [("TextEdit", None)]


def test_close_unknown_app(fake):
    result = run_line("close notpad")
    assert not result.ok and "notepad" in result.message


def test_cannot_close_a_website(fake):
    result = run_line("close youtube")
    assert not result.ok and "tab" in result.message
    assert fake.closed == []


def test_close_when_not_running(fake):
    fake.error = "I don't see notepad.exe running."
    assert "don't see" in run_line("close notepad").message


def test_close_needs_a_name(fake):
    assert "Close what?" in run_line("close").message


def test_close_mentions_unsaved_work(fake):
    assert "unsaved" in run_line("close notepad").message


# --- music and volume ----------------------------------------------------------------------------------


@pytest.mark.parametrize("word, action", [
    ("play", "play"), ("resume", "play"), ("pause", "pause"), ("stop", "pause"),
    ("next", "next"), ("skip", "next"),
    ("prev", "previous"), ("previous", "previous"), ("back", "previous"),
])
def test_music_actions(fake, word, action):
    assert run_line(f"music {word}").ok
    assert fake.media_actions == [action]


def test_windows_play_pause_note(fake):
    assert "flips" in run_line("music play").message
    assert "flips" not in run_line("music next").message


def test_no_windows_note_elsewhere(fake):
    fake.key = "linux"
    assert "flips" not in run_line("music play").message


@pytest.mark.parametrize("line, level", [("music vol 15", 15), ("music vol 50", 50),
                                          ("music volume 30", 30), ("music vol 50%", 50),
                                          ("music vol 0", 0)])
def test_music_volume(fake, line, level):
    assert run_line(line).ok
    assert fake.volumes == [(level, True)]


@pytest.mark.parametrize("line", ["music vol", "music vol 150", "music vol loud", "music vol -5"])
def test_bad_music_volume(fake, line):
    assert not run_line(line).ok
    assert fake.volumes == []


def test_system_volume(fake):
    result = run_line("volume 30")
    assert result.ok and "system volume" in result.message
    assert fake.volumes == [(30, False)]


def test_volume_without_a_number(fake):
    assert "0 to 100" in run_line("volume").message


def test_unknown_music_word(fake):
    result = run_line("music dance")
    assert not result.ok and "music play" in result.message


def test_music_alone_explains(fake):
    assert "music play" in run_line("music").message


def test_music_platform_errors(fake):
    fake.error = "I need 'playerctl' installed"
    assert "playerctl" in run_line("music next").message
    assert "playerctl" in run_line("music vol 10").message


def test_music_in_a_chain(fake):
    from shelly.core.engine import run_chain

    run_chain("music pause and open youtube", lambda r: r)
    assert fake.media_actions == ["pause"] and fake.urls


# --- delete (to the trash) ---------------------------------------------------------------------------------


def test_delete_asks_first(work, fake):
    (work / "a.txt").write_text("x")
    result = run_line("delete a.txt")
    assert result.ask.prompt == "Move 'a.txt' to the trash?"
    assert (work / "a.txt").exists()


def test_yes_moves_it_to_the_trash(work, fake):
    (work / "a.txt").write_text("x")
    result = answer(run_line("delete a.txt").ask, "yes")
    assert result.ok and "trash" in result.message
    assert fake.trashed[0].name == "a.txt"
    assert not (work / "a.txt").exists()


def test_no_keeps_it(work, fake):
    (work / "a.txt").write_text("x")
    answer(run_line("delete a.txt").ask, "no")
    assert (work / "a.txt").exists() and fake.trashed == []


def test_deleting_a_folder_says_so(work):
    (work / "src").mkdir()
    assert "everything in it" in run_line("delete src").ask.prompt


def test_delete_several_asks_once(work, fake):
    (work / "a.txt").write_text("x")
    (work / "b.txt").write_text("x")
    result = run_line("delete a.txt and b.txt")
    assert "2 things" in result.ask.prompt
    answer(result.ask, "yes")
    assert [p.name for p in fake.trashed] == ["a.txt", "b.txt"]


@pytest.mark.parametrize("verb", ["rm", "del", "trash", "erase", "remove", "delete"])
def test_delete_aliases(work, verb):
    (work / "a.txt").write_text("x")
    assert run_line(f"{verb} a.txt").ask is not None


def test_delete_in_a_place(work, fake):
    (work / "docs").mkdir()
    (work / "docs" / "a.txt").write_text("x")
    answer(run_line("delete a.txt in docs").ask, "yes")
    assert not (work / "docs" / "a.txt").exists()


def test_important_folders_cannot_be_deleted(work):
    (work.parent / "home" / "Downloads").mkdir()
    result = run_line("delete downloads")
    assert result.ask is None and "important" in result.message


def test_delete_missing_thing_suggests(work):
    (work / "notes.txt").write_text("x")
    assert "notes.txt" in run_line("delete notes.tx").message


def test_delete_without_a_name(work):
    assert "Delete what?" in run_line("delete").message


def test_trash_failures_are_reported(work, fake):
    (work / "a.txt").write_text("x")
    result = run_line("delete a.txt")
    fake.error = "No Recycle Bin here."
    final = answer(result.ask, "yes")
    assert not final.ok and "Recycle Bin" in final.message
    assert (work / "a.txt").exists()


# --- replace now uses the trash ----------------------------------------------------------------------------


def clash(work):
    (work / "a.txt").write_text("new")
    (work / "dst").mkdir()
    (work / "dst" / "a.txt").write_text("old")


def test_replace_sends_the_old_one_to_the_trash(work, fake):
    clash(work)
    ask = run_line("copy a.txt to dst").ask
    result = answer(ask, "replace")
    assert [(p.parent.name, p.name) for p in fake.trashed] == [("dst", "a.txt")]
    assert "it's in the trash" in result.message
    assert (work / "dst" / "a.txt").read_text() == "new"


def test_if_the_trash_fails_replace_changes_nothing(work, fake):
    clash(work)
    ask = run_line("copy a.txt to dst").ask
    fake.error = "No trash."
    result = answer(ask, "replace")
    assert not result.ok and "trash" in result.message
    assert (work / "dst" / "a.txt").read_text() == "old"
    assert [p.name for p in (work / "dst").iterdir()] == ["a.txt"]


def test_if_the_trash_fails_a_move_puts_the_source_back(work, fake):
    clash(work)
    ask = run_line("move a.txt to dst").ask
    fake.error = "No trash."
    answer(ask, "replace")
    assert (work / "a.txt").read_text() == "new"
    assert (work / "dst" / "a.txt").read_text() == "old"


# --- help --------------------------------------------------------------------------------------------------------


def test_help_overview():
    message = run_line("help").message
    assert "help <topic>" in message and "music" in message


def test_help_topics():
    assert "go to downloads" in run_line("help go").message
    assert "go to downloads" in run_line("help cd").message
    assert "paste" in run_line("help cut").message
    assert "in brave" in run_line("help open").message


def test_help_guesses_misspelled_topics():
    assert "list" in run_line("help lst").message.lower()


def test_help_for_nothing_known():
    assert not run_line("help zzzzzzzz").ok


def test_question_mark_is_help():
    assert run_line("?").ok


def test_every_help_alias_points_at_a_real_topic():
    from shelly.commands.helpcmd import ALIASES, TOPICS

    assert set(ALIASES.values()) <= set(TOPICS)


# --- tab completion --------------------------------------------------------------------------------------------------


def test_complete_commands():
    found = completion.complete("g", "g")
    assert "go" in found and "goto" in found
    assert completion.complete("", "") != []


def test_complete_app_names_after_open(fake):
    assert "youtube" in completion.complete("open y", "y")
    assert "chrome" in completion.complete("close ch", "ch")


def test_complete_files_and_folders(work):
    (work / "report.txt").write_text("x")
    (work / "reports").mkdir()
    found = completion.complete("copy rep", "rep")
    assert "report.txt" in found and f"reports{os.sep}" in found


def test_complete_ignores_capitals(work):
    (work / "Readme.md").write_text("x")
    assert "Readme.md" in completion.complete("show read", "read")


def test_names_with_spaces_are_quoted(work):
    (work / "my notes.txt").write_text("x")
    assert '"my notes.txt"' in completion.complete("show my", "my")


def test_complete_inside_a_folder(work):
    (work / "sub").mkdir()
    (work / "sub" / "inner.txt").write_text("x")
    assert "sub/inner.txt" in completion.complete("show sub/in", "sub/in")


def test_complete_known_folders(work):
    assert "downloads" in completion.complete("go dow", "dow")


def test_setup_never_crashes():
    completion.setup()
