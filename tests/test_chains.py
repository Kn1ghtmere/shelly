from pathlib import Path

import pytest

from shelly.core import paths, registry, session
from shelly.core.engine import answer, run_chain, run_line
from shelly.core.parser import parse_chain, parse_line
from shelly.core.result import Result


def settle_yes(result: Result) -> Result:
    while result.ask is not None:
        result = answer(result.ask, "yes")
    return result


def passthrough(result: Result) -> Result:
    return result


# --- parser: 'in' chains ----------------------------------------------------------


def test_in_chain_is_kept_in_order():
    intent = parse_line("go to tools in assets in D:")
    assert intent.verb == "go"
    assert intent.args == ["tools"]
    assert intent.containers == {"": ["assets", "D:"]}


def test_in_binds_to_whatever_it_follows():
    intent = parse_line("copy a.txt in docs to backup in E:")
    assert intent.containers == {"": ["docs"], "to": ["E:"]}
    assert intent.options["to"] == "backup"


def test_in_with_no_name():
    assert parse_line("list in downloads").containers == {"": ["downloads"]}


def test_no_in_means_no_containers():
    assert parse_line("go to tools").containers == {}


# --- parser: and / and then ----------------------------------------------------------


def names(chain):
    return [[i.verb for i in stage] for stage in chain.stages]


def test_and_makes_one_stage_with_two_commands():
    assert names(parse_chain("open yt and open spotify")) == [["open", "open"]]


def test_and_then_makes_two_stages():
    assert names(parse_chain("open yt and then open spotify")) == [["open"], ["open"]]


def test_mixed():
    chain = parse_chain("open yt and open spotify and then go to downloads")
    assert names(chain) == [["open", "open"], ["go"]]


def test_and_between_things_is_not_a_split():
    chain = parse_chain("copy a.txt and b.txt")
    assert names(chain) == [["copy"]]
    assert chain.stages[0][0].args == ["a.txt", "and", "b.txt"]


def test_and_inside_a_query_is_not_a_split():
    assert names(parse_chain("play rock and roll")) == [["play"]]


def test_quoted_and_is_never_a_split():
    assert names(parse_chain('open youtube search "this and open that"')) == [["open"]]


def test_each_command_keeps_its_own_text():
    chain = parse_chain('make a folder called "my stuff" and then go to "my stuff"')
    assert chain.stages[0][0].raw == 'make a folder called "my stuff"'
    assert chain.stages[1][0].raw == 'go to "my stuff"'


def test_and_then_needs_something_after_it():
    from shelly.core.errors import ParseError

    with pytest.raises(ParseError):
        parse_chain("open yt and then")


def test_blank_line_is_an_empty_chain():
    assert parse_chain("   ").stages == []


# --- running chains --------------------------------------------------------------------


def test_and_runs_both(work, fake):
    results = run_chain("open yt and open spotify", passthrough)
    assert [r.ok for r in results] == [True, True]
    assert fake.urls == ["https://www.youtube.com", "https://open.spotify.com"]


def test_and_then_runs_in_order(work):
    results = run_chain("make a folder called x and then go to x", passthrough)
    assert all(r.ok for r in results)
    assert Path.cwd().samefile(work / "x")


def test_and_then_stops_after_a_failure(work):
    results = run_chain("go to nope and then make a folder called y", passthrough)
    assert not (work / "y").exists()
    assert "didn't run" in results[-1].message


def test_and_keeps_going_after_a_failure(work):
    run_chain("go to nope and make a folder called y", passthrough)
    assert (work / "y").is_dir()


def test_and_then_waits_for_a_question_to_be_answered(work):
    (work / "a.txt").write_text("x")
    results = run_chain("move a.txt to docs and then list in docs", settle_yes)
    assert "a.txt" in results[-1].message


def test_a_question_that_is_refused_stops_the_line(work):
    (work / "a.txt").write_text("x")

    def settle_no(result):
        while result.ask is not None:
            result = answer(result.ask, "no")
        return result

    results = run_chain("move a.txt to docs and then make a folder called after", settle_no)
    assert (work / "a.txt").exists()
    assert not (work / "after").exists()
    assert "didn't run" in results[-1].message


def test_exit_in_a_chain(work):
    results = run_chain("hello and then bye", passthrough)
    assert results[-1].should_exit


def test_parse_errors_in_a_chain_are_reported(work):
    assert not run_chain('say "oops', passthrough)[0].ok


def test_a_crashing_command_does_not_end_the_shell(monkeypatch):
    def boom(intent):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(registry._commands, "boom", boom)
    result = run_line("boom")
    assert not result.ok
    assert "kaboom" in result.message


# --- 'in' chains in commands ---------------------------------------------------------------


@pytest.fixture
def tree(work):
    (work / "assets" / "tools").mkdir(parents=True)
    (work / "docs").mkdir()
    return work


def test_go_through_a_chain(tree):
    assert run_line("go to tools in assets").ok
    assert Path.cwd().samefile(tree / "assets" / "tools")


def test_chain_ending_at_an_absolute_place(tree):
    assert run_line(f'go to tools in assets in "{tree}"').ok
    assert Path.cwd().samefile(tree / "assets" / "tools")


def test_chain_ignores_capitals(tree):
    assert run_line("go to TOOLS in Assets").ok


def test_go_in_a_folder_with_no_name(tree):
    assert run_line("go in assets").ok
    assert Path.cwd().samefile(tree / "assets")


def test_missing_link_names_the_place_and_suggests(tree):
    result = run_line("go to tolls in assets")
    assert not result.ok
    assert "can't find 'tolls' in" in result.message
    assert "tools" in result.message


def test_missing_outer_folder(tree):
    result = run_line("go to tools in nope")
    assert "can't find 'nope'" in result.message


def test_a_file_in_the_middle_of_a_chain(tree):
    (tree / "f.txt").write_text("x")
    assert "is a file, not a folder" in run_line("go to tools in f.txt").message


def test_list_through_a_chain(tree):
    (tree / "assets" / "tools" / "hammer.txt").write_text("x")
    assert "hammer.txt" in run_line("list in tools in assets").message
    assert "hammer.txt" in run_line("list tools in assets").message


def test_make_things_in_a_chain(tree):
    assert run_line("make a folder called x in tools in assets").ok
    assert (tree / "assets" / "tools" / "x").is_dir()
    assert run_line("make a file called a.txt in tools in assets").ok
    assert (tree / "assets" / "tools" / "a.txt").exists()


def test_copy_into_a_chain(tree):
    (tree / "a.txt").write_text("x")
    assert run_line("copy a.txt to tools in assets").ok
    assert (tree / "assets" / "tools" / "a.txt").exists()


def test_copy_out_of_a_chain(tree):
    (tree / "assets" / "r.txt").write_text("x")
    assert run_line("copy r.txt in assets to docs").ok
    assert (tree / "docs" / "r.txt").exists()


def test_paste_forms_with_chains(tree):
    (tree / "a.txt").write_text("x")
    run_line("copy a.txt")
    assert run_line("paste to tools in assets").ok
    assert run_line("paste in docs").ok
    (tree / "docs" / "a.txt").unlink()
    assert run_line("paste docs").ok


def test_move_into_a_missing_folder_inside_a_chain_asks(tree):
    (tree / "a.txt").write_text("x")
    result = run_line("move a.txt to fresh in assets")
    assert "no folder named" in result.ask.prompt
    answer(result.ask, "yes")
    assert (tree / "assets" / "fresh" / "a.txt").exists()


def test_show_and_rename_through_a_chain(tree, fake):
    (tree / "assets" / "x.txt").write_text("x")
    assert run_line("show x.txt in assets").ok
    assert fake.revealed[0].samefile(tree / "assets" / "x.txt")
    assert run_line("rename x.txt in assets to y.txt").ok
    assert (tree / "assets" / "y.txt").exists()


def test_rename_cannot_use_a_destination_chain(tree):
    (tree / "x.txt").write_text("x")
    assert not run_line("rename x.txt to y.txt in docs").ok


# --- long listings -------------------------------------------------------------------------


@pytest.fixture
def crowded(work):
    for number in range(120):
        (work / f"f{number:03}.txt").write_text("x")
    return work


def test_list_shows_a_page_and_says_how_to_continue(crowded):
    lines = run_line("list").message.splitlines()
    assert sum(1 for line in lines if "f0" in line or "f1" in line) == 50
    assert "...and 70 more. Say 'more'" in lines[-1]


def test_more_shows_the_next_pages(crowded):
    run_line("list")
    second = run_line("more").message
    assert "f050.txt" in second and "...and 20 more" in second
    third = run_line("more").message
    assert "f119.txt" in third and "more." not in third
    assert not run_line("more").ok


def test_list_all_shows_everything(crowded):
    message = run_line("list all").message
    assert "f000.txt" in message and "f119.txt" in message
    assert "more." not in message


def test_a_new_list_starts_over(crowded):
    run_line("list")
    run_line("list")
    assert "f050.txt" in run_line("more").message


def test_quoting_lets_you_list_a_folder_called_all(crowded):
    (crowded / "all").mkdir()
    (crowded / "all" / "inside.txt").write_text("x")
    assert "inside.txt" in run_line('list "all"').message


def test_more_with_nothing_listed(work):
    assert not run_line("more").ok


def test_show_more_is_more(crowded):
    run_line("list")
    assert "f050.txt" in run_line("show more").message


# --- 'and' for lists --------------------------------------------------------------------------


def test_copy_several_things(work):
    (work / "a.txt").write_text("a")
    (work / "b.txt").write_text("b")
    (work / "dst").mkdir()
    result = run_line("copy a.txt and b.txt")
    assert "a.txt, b.txt" in result.message
    assert run_line("paste to dst").ok
    assert (work / "dst" / "a.txt").exists() and (work / "dst" / "b.txt").exists()


def test_items_with_spaces_need_no_quotes_when_joined_by_and(work):
    (work / "my file.txt").write_text("a")
    (work / "b.txt").write_text("b")
    assert run_line("copy my file.txt and b.txt").ok
    assert [p.name for p in session.get_clipboard().items] == ["my file.txt", "b.txt"]


def test_cut_and_move_several_things(work):
    (work / "a.txt").write_text("a")
    (work / "b.txt").write_text("b")
    (work / "dst").mkdir()
    assert run_line("move a.txt and b.txt to dst").ok
    assert (work / "dst" / "a.txt").exists() and (work / "dst" / "b.txt").exists()
    assert not (work / "a.txt").exists()


def test_cut_several_then_paste_clears_the_clipboard(work):
    (work / "a.txt").write_text("a")
    (work / "b.txt").write_text("b")
    (work / "dst").mkdir()
    run_line("cut a.txt and b.txt")
    run_line("paste to dst")
    assert session.get_clipboard() is None


def test_several_things_without_and_still_means_forgotten_quotes(work):
    result = run_line("copy my file.txt")
    assert "put it in quotes" in result.message


def test_a_missing_item_in_a_list_is_reported(work):
    (work / "a.txt").write_text("a")
    result = run_line("copy a.txt and nope.txt")
    assert not result.ok and "nope.txt" in result.message


# --- answers with no question, and misspelled commands ---------------------------------------


@pytest.mark.parametrize("line", ["yes", "no", "keep both", "cancel", "no thanks", "replace"])
def test_an_answer_with_no_question(line):
    result = run_line(line)
    assert not result.ok
    assert "not asking anything" in result.message


def test_other_unknown_commands_are_still_unknown():
    assert "don't know 'create'" in run_line("create widget").message


def test_misspelled_commands_get_a_suggestion():
    assert "Did you mean 'list'?" in run_line("lst").message
    assert "Did you mean 'copy'?" in run_line("copi").message
    assert "Type help" in run_line("blorp").message
