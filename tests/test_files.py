from pathlib import Path

from shelly.core.engine import run_line


def here() -> Path:
    return Path.cwd()


# --- go / back / where --------------------------------------------------


def test_go_into_a_folder(work):
    (work / "projects").mkdir()
    result = run_line("go to projects")
    assert result.ok
    assert here().samefile(work / "projects")


def test_go_ignores_capital_letters(work):
    (work / "Projects").mkdir()
    assert run_line("go projects").ok
    assert here().samefile(work / "Projects")


def test_go_back(work):
    (work / "a").mkdir()
    run_line("go a")
    assert run_line("go back").ok
    assert here().samefile(work)


def test_back_with_no_history(work):
    assert not run_line("back").ok


def test_go_up_and_dotdot(work):
    (work / "a").mkdir()
    run_line("go a")
    run_line("go up")
    assert here().samefile(work)
    run_line("go a")
    run_line("cd ..")
    assert here().samefile(work)


def test_go_alone_goes_home(work):
    run_line("go")
    assert here().samefile(work.parent / "home")


def test_go_to_known_folder(work):
    (work.parent / "home" / "Downloads").mkdir()
    assert run_line("go to downloads").ok
    assert here().samefile(work.parent / "home" / "Downloads")


def test_go_to_a_file_is_refused(work):
    (work / "a.txt").write_text("x")
    result = run_line("go a.txt")
    assert not result.ok
    assert "file" in result.message


def test_go_typo_suggests(work):
    result = run_line("go dowloads")
    assert not result.ok
    assert "downloads" in result.message


def test_go_two_words_suggests_quotes(work):
    (work / "my folder").mkdir()
    result = run_line("go my folder")
    assert not result.ok
    assert 'go "my folder"' in result.message
    assert run_line('go "my folder"').ok


def test_go_rejects_stray_options(work):
    assert not run_line("go downloads in somewhere").ok


def test_where_am_i(work):
    result = run_line("where am i")
    assert result.ok
    assert Path(result.message).samefile(work)


# --- list ---------------------------------------------------------------


def test_list_empty_folder(work):
    assert "(empty)" in run_line("list").message


def test_list_puts_folders_first_and_marks_them(work):
    (work / "zeta").mkdir()
    (work / "alpha.txt").write_text("hello")
    lines = run_line("show files").message.splitlines()[1:]
    assert lines[0].strip() == "zeta/"
    assert lines[1].strip().startswith("alpha.txt")
    assert "5 B" in lines[1]


def test_list_a_folder_two_ways(work):
    (work / "sub").mkdir()
    (work / "sub" / "x.txt").write_text("x")
    assert "x.txt" in run_line("list sub").message
    assert "x.txt" in run_line("list in sub").message


def test_list_both_ways_at_once_is_refused(work):
    (work / "sub").mkdir()
    assert not run_line("list sub in sub").ok


def test_list_missing_folder(work):
    (work / "projects").mkdir()
    result = run_line("list projcts")
    assert not result.ok
    assert "projects" in result.message


def test_list_a_file_is_refused(work):
    (work / "a.txt").write_text("x")
    assert not run_line("list a.txt").ok


def test_list_returns_names_as_data(work):
    (work / "a.txt").write_text("x")
    assert run_line("list").data == ["a.txt"]


# --- mkdir --------------------------------------------------------------


def test_make_a_folder_with_natural_words(work):
    assert run_line("make a folder called projects").ok
    assert (work / "projects").is_dir()


def test_make_a_folder_with_spaces_needs_quotes(work):
    result = run_line("make a folder called my stuff")
    assert not result.ok
    assert 'make a folder called "my stuff"' in result.message
    assert run_line('make a folder called "my stuff"').ok
    assert (work / "my stuff").is_dir()


def test_make_nested_folders(work):
    assert run_line("mkdir a/b/c").ok
    assert (work / "a" / "b" / "c").is_dir()


def test_make_folder_in_another_folder(work):
    (work / "documents").mkdir()
    assert run_line("make folder projects in documents").ok
    assert (work / "documents" / "projects").is_dir()


def test_make_existing_folder_is_refused(work):
    (work / "a").mkdir()
    assert not run_line("mkdir a").ok


def test_make_folder_without_a_name(work):
    assert not run_line("mkdir").ok


# --- copy ---------------------------------------------------------------


def test_copy_file_into_folder(work):
    (work / "a.txt").write_text("hello")
    (work / "backup").mkdir()
    assert run_line("copy a.txt to backup").ok
    assert (work / "a.txt").exists()
    assert (work / "backup" / "a.txt").read_text() == "hello"


def test_copy_file_to_a_new_name(work):
    (work / "a.txt").write_text("hello")
    assert run_line("cp a.txt to b.txt").ok
    assert (work / "b.txt").read_text() == "hello"


def test_copy_folder(work):
    (work / "src").mkdir()
    (work / "src" / "x.txt").write_text("x")
    assert run_line("copy src to dst").ok
    assert (work / "dst" / "x.txt").exists()


def test_copy_never_overwrites(work):
    (work / "a.txt").write_text("new")
    (work / "backup").mkdir()
    (work / "backup" / "a.txt").write_text("old")
    result = run_line("copy a.txt to backup")
    assert not result.ok
    assert "overwrite" in result.message
    assert (work / "backup" / "a.txt").read_text() == "old"


def test_copy_folder_into_itself_is_refused(work):
    (work / "src").mkdir()
    assert not run_line("copy src to src/inner").ok


def test_copy_to_a_missing_folder(work):
    (work / "a.txt").write_text("x")
    result = run_line("copy a.txt to nope/b.txt")
    assert not result.ok
    assert "can't find the folder" in result.message


def test_copy_typo_suggests(work):
    (work / "a.txt").write_text("x")
    result = run_line("copy a.txtt to backup")
    assert "a.txt" in result.message


def test_copy_without_to_explains(work):
    (work / "a.txt").write_text("x")
    assert "Try: copy" in run_line("copy a.txt").message


def test_copy_with_spaces_suggests_quotes(work):
    result = run_line("copy my file.txt to backup")
    assert 'copy "my file.txt" to backup' in result.message


# --- move ---------------------------------------------------------------


def test_move_file_into_folder(work):
    (work / "a.txt").write_text("hello")
    (work / "backup").mkdir()
    assert run_line("move a.txt to backup").ok
    assert not (work / "a.txt").exists()
    assert (work / "backup" / "a.txt").read_text() == "hello"


def test_move_to_a_new_name(work):
    (work / "a.txt").write_text("hello")
    assert run_line("mv a.txt to b.txt").ok
    assert (work / "b.txt").exists()


def test_move_never_overwrites(work):
    (work / "a.txt").write_text("new")
    (work / "backup").mkdir()
    (work / "backup" / "a.txt").write_text("old")
    assert not run_line("move a.txt to backup").ok
    assert (work / "a.txt").exists()


def test_move_folder(work):
    (work / "src").mkdir()
    (work / "src" / "x.txt").write_text("x")
    (work / "dst").mkdir()
    assert run_line("move src to dst").ok
    assert (work / "dst" / "src" / "x.txt").exists()


def test_move_protects_important_folders(work):
    (work.parent / "home" / "Downloads").mkdir()
    result = run_line("move downloads to somewhere")
    assert not result.ok
    assert "important" in result.message
    assert (work.parent / "home" / "Downloads").exists()


def test_move_protects_the_folder_you_are_in(work):
    assert not run_line("move . to elsewhere").ok


# --- rename -------------------------------------------------------------


def test_rename(work):
    (work / "a.txt").write_text("x")
    assert run_line("rename a.txt to b.txt").ok
    assert (work / "b.txt").exists() and not (work / "a.txt").exists()


def test_rename_never_overwrites(work):
    (work / "a.txt").write_text("1")
    (work / "b.txt").write_text("2")
    assert not run_line("rename a.txt to b.txt").ok
    assert (work / "b.txt").read_text() == "2"


def test_rename_cannot_move(work):
    (work / "a.txt").write_text("x")
    result = run_line('rename a.txt to "sub/b.txt"')
    assert not result.ok
    assert "move" in result.message


def test_rename_only_changing_capitals(work):
    (work / "a.txt").write_text("x")
    assert run_line("rename a.txt to A.txt").ok
    assert "A.txt" in run_line("list").data


def test_rename_protects_important_folders(work):
    (work.parent / "home" / "Downloads").mkdir()
    assert not run_line("rename downloads to stuff").ok


def test_rename_without_to_explains(work):
    assert "Try: rename" in run_line("rename a.txt").message


# --- the "destination doesn't exist" trap -------------------------------


def test_move_to_a_missing_folder_says_it_became_a_new_name(work):
    (work / "a.txt").write_text("x")
    result = run_line("move a.txt to documents")
    assert result.ok
    assert (work / "documents").is_file()
    assert "new name" in result.message


def test_copy_to_a_missing_folder_says_it_became_a_new_name(work):
    (work / "a.txt").write_text("x")
    assert "new name" in run_line("copy a.txt to documents").message


def test_move_into_a_real_folder_has_no_warning(work):
    (work / "a.txt").write_text("x")
    (work / "documents").mkdir()
    assert "new name" not in run_line("move a.txt to documents").message
