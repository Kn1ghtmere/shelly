from pathlib import Path

from shelly.core import session, transfer
from shelly.core.engine import answer, run_line


def reply(line, said):
    """Run a line that asks a question, give an answer, return the final result."""
    result = run_line(line)
    assert result.ask is not None, f"expected a question, got: {result.message}"
    return answer(result.ask, said)


# --- copy + paste ---------------------------------------------------------------


def test_copy_then_paste_into_another_folder(work):
    (work / "a.txt").write_text("hello")
    (work / "sub").mkdir()
    run_line("copy a.txt")
    run_line("go sub")
    assert run_line("paste").ok
    assert (work / "sub" / "a.txt").read_text() == "hello"
    assert (work / "a.txt").exists()


def test_a_copy_can_be_pasted_again(work):
    (work / "a.txt").write_text("hello")
    (work / "one").mkdir()
    (work / "two").mkdir()
    run_line("copy a.txt")
    run_line("paste to one")
    run_line("paste to two")
    assert (work / "one" / "a.txt").exists() and (work / "two" / "a.txt").exists()


def test_paste_forms(work):
    (work / "a.txt").write_text("x")
    for folder in ("p1", "p2", "p3"):
        (work / folder).mkdir()
    run_line("copy a.txt")
    assert run_line("paste p1").ok
    assert run_line("paste to p2").ok
    assert run_line("paste in p3").ok
    for folder in ("p1", "p2", "p3"):
        assert (work / folder / "a.txt").exists()


def test_paste_here_in_the_same_folder_offers_a_duplicate(work):
    (work / "a.txt").write_text("hello")
    run_line("copy a.txt")
    result = run_line("paste")
    assert result.ask.hint == "keep both / cancel"
    answer(result.ask, "keep both")
    assert (work / "a (2).txt").read_text() == "hello"


def test_paste_here_word_means_current_folder(work):
    (work / "a.txt").write_text("hello")
    run_line("copy a.txt")
    assert run_line("paste here").ask is not None


def test_paste_with_nothing_copied(work):
    result = run_line("paste")
    assert not result.ok
    assert "nothing to paste" in result.message


def test_paste_to_two_places_is_refused(work):
    (work / "a.txt").write_text("x")
    run_line("copy a.txt")
    assert not run_line("paste one to two").ok
    assert not run_line("paste one in two").ok


def test_copied_folder_pastes_with_contents(work):
    (work / "src").mkdir()
    (work / "src" / "x.txt").write_text("x")
    (work / "dst").mkdir()
    run_line("copy src")
    run_line("paste to dst")
    assert (work / "dst" / "src" / "x.txt").exists()


def test_source_deleted_before_pasting(work):
    (work / "a.txt").write_text("x")
    (work / "sub").mkdir()
    run_line("copy a.txt")
    (work / "a.txt").unlink()
    result = run_line("paste to sub")
    assert not result.ok
    assert "isn't there anymore" in result.message


# --- cut + paste -----------------------------------------------------------------


def test_cut_does_nothing_until_you_paste(work):
    (work / "a.txt").write_text("x")
    assert run_line("cut a.txt").ok
    assert (work / "a.txt").exists()


def test_cut_then_paste_moves_it(work):
    (work / "a.txt").write_text("hello")
    (work / "sub").mkdir()
    run_line("cut a.txt")
    assert run_line("paste to sub").ok
    assert not (work / "a.txt").exists()
    assert (work / "sub" / "a.txt").read_text() == "hello"


def test_a_cut_can_only_be_pasted_once(work):
    (work / "a.txt").write_text("x")
    (work / "one").mkdir()
    (work / "two").mkdir()
    run_line("cut a.txt")
    run_line("paste to one")
    assert session.get_clipboard() is None
    assert not run_line("paste to two").ok


def test_pasting_a_cut_back_where_it_is_does_nothing(work):
    (work / "a.txt").write_text("x")
    run_line("cut a.txt")
    result = run_line("paste")
    assert result.ok
    assert "already in" in result.message
    assert (work / "a.txt").exists()


def test_cutting_important_folders_is_refused(work):
    (work.parent / "home" / "Downloads").mkdir()
    assert not run_line("cut downloads").ok


def test_cut_without_a_name(work):
    assert "Cut what?" in run_line("cut").message


# --- missing folders -----------------------------------------------------------------


def test_missing_folder_prompt_wording(work):
    (work / "a.txt").write_text("x")
    run_line("copy a.txt")
    prompt = run_line("paste to documents").ask.prompt
    assert prompt.startswith("There is no folder named 'documents' in '")
    assert prompt.endswith("Would you like me to create one and continue?")


def test_yes_creates_the_folder_and_continues(work):
    (work / "a.txt").write_text("x")
    run_line("copy a.txt")
    result = reply("paste to documents", "yes")
    assert result.ok
    assert (work / "documents" / "a.txt").exists()


def test_no_creates_nothing(work):
    (work / "a.txt").write_text("x")
    run_line("copy a.txt")
    reply("paste to documents", "no")
    assert not (work / "documents").exists()


def test_a_cut_stays_on_the_clipboard_if_you_say_no(work):
    (work / "a.txt").write_text("x")
    run_line("cut a.txt")
    reply("paste to documents", "nope")
    assert session.get_clipboard() is not None
    assert (work / "a.txt").exists()


def test_deeper_missing_paths_name_the_whole_missing_part(work):
    (work / "a.txt").write_text("x")
    prompt = run_line("copy a.txt to one/two").ask.prompt
    assert "'one" in prompt and "two" in prompt
    reply("copy a.txt to one/two", "yes")
    assert (work / "one" / "two" / "a.txt").exists()


def test_a_wrong_location_can_be_corrected(work):
    (work / "a.txt").write_text("x")
    (work / "docs").mkdir()
    reply("move a.txt to dcos", "no")
    assert run_line("move a.txt to docs").ok
    assert (work / "docs" / "a.txt").exists()


def test_a_file_where_a_folder_should_be(work):
    (work / "a.txt").write_text("x")
    (work / "b.txt").write_text("y")
    (work / "box").write_text("not a folder")
    result = run_line("copy a.txt to box/inner")
    assert result.ask is not None or not result.ok


# --- name clashes ---------------------------------------------------------------------


def clash(work):
    (work / "a.txt").write_text("new")
    (work / "dst").mkdir()
    (work / "dst" / "a.txt").write_text("old")


def test_replace(work):
    clash(work)
    result = reply("copy a.txt to dst", "replace")
    assert (work / "dst" / "a.txt").read_text() == "new"
    assert "replaced the old one" in result.message
    assert not list((work / "dst").glob("*.shelly-new"))


def test_keep_both(work):
    clash(work)
    reply("copy a.txt to dst", "keep both")
    assert (work / "dst" / "a.txt").read_text() == "old"
    assert (work / "dst" / "a (2).txt").read_text() == "new"


def test_keep_both_keeps_counting(work):
    clash(work)
    (work / "dst" / "a (2).txt").write_text("two")
    reply("copy a.txt to dst", "both")
    assert (work / "dst" / "a (3).txt").read_text() == "new"


def test_cancel_changes_nothing(work):
    clash(work)
    reply("copy a.txt to dst", "cancel")
    assert (work / "dst" / "a.txt").read_text() == "old"
    assert [p.name for p in (work / "dst").iterdir()] == ["a.txt"]


def test_move_replace_removes_the_source(work):
    clash(work)
    reply("move a.txt to dst", "replace")
    assert not (work / "a.txt").exists()
    assert (work / "dst" / "a.txt").read_text() == "new"


def test_move_keep_both(work):
    clash(work)
    reply("move a.txt to dst", "keep both")
    assert not (work / "a.txt").exists()
    assert (work / "dst" / "a (2).txt").exists()


def test_replacing_a_folder_swaps_the_whole_thing(work):
    (work / "src").mkdir()
    (work / "src" / "new.txt").write_text("n")
    (work / "dst" / "src").mkdir(parents=True)
    (work / "dst" / "src" / "old.txt").write_text("o")
    reply("copy src to dst", "replace")
    assert (work / "dst" / "src" / "new.txt").exists()
    assert not (work / "dst" / "src" / "old.txt").exists()


def test_keep_both_for_folders(work):
    (work / "src").mkdir()
    (work / "dst" / "src").mkdir(parents=True)
    reply("copy src to dst", "keep both")
    assert (work / "dst" / "src (2)").is_dir()


def test_clash_on_a_named_file_target(work):
    (work / "a.txt").write_text("new")
    (work / "b.txt").write_text("old")
    reply("copy a.txt to b.txt", "keep both")
    assert (work / "b (2).txt").read_text() == "new"
    assert (work / "b.txt").read_text() == "old"


def test_cancel_after_a_clipboard_cut_keeps_the_source(work):
    clash(work)
    run_line("cut a.txt")
    reply("paste to dst", "cancel")
    assert (work / "a.txt").exists()
    assert session.get_clipboard() is not None


# --- safety checks happen before any question -----------------------------------------


def test_folder_into_itself_is_refused_without_asking(work):
    (work / "src").mkdir()
    result = run_line("copy src to src/inner")
    assert result.ask is None
    assert not result.ok


def test_protected_folders_are_refused_without_asking(work):
    (work.parent / "home" / "Downloads").mkdir()
    result = run_line("move downloads to elsewhere")
    assert result.ask is None
    assert "important" in result.message


# --- small helpers ---------------------------------------------------------------------


def test_unique_name_for_files_and_folders(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "d").mkdir()
    assert transfer.unique_name(tmp_path / "a.txt").name == "a (2).txt"
    assert transfer.unique_name(tmp_path / "d").name == "d (2)"


def test_split_missing(tmp_path):
    (tmp_path / "real").mkdir()
    location, name = transfer.split_missing(tmp_path / "real" / "x" / "y")
    assert location == tmp_path / "real"
    assert Path(name) == Path("x") / "y"


def test_new_name_detection(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    d = tmp_path / "d"
    d.mkdir()
    assert transfer.looks_like_file_name("b.txt", f)
    assert not transfer.looks_like_file_name("backup", f)
    assert not transfer.looks_like_file_name("b.txt", d)
