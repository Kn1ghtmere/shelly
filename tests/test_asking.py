import builtins

import pytest

from shelly.core.engine import answer, run_line
from shelly.core.result import Ask, Result
from shelly.ui import terminal


def yes_no():
    return Ask.yes_no("Sure?", lambda: Result.success("did it"), lambda: Result.success("didn't"))


@pytest.mark.parametrize("reply", ["yes", "y", "Yeah!", "sure", "ok", "go ahead", "yes please", "Do it", "  YES  "])
def test_agreeing_words(reply):
    assert answer(yes_no(), reply).message == "did it"


@pytest.mark.parametrize("reply", ["no", "n", "nope", "cancel", "no thanks", "don't", "nevermind", "Never mind."])
def test_disagreeing_words(reply):
    assert answer(yes_no(), reply).message == "didn't"


@pytest.mark.parametrize("reply", ["banana", "", "   ", "maybe"])
def test_unclear_answers_are_not_guessed(reply):
    assert answer(yes_no(), reply) is None


def test_default_no_does_nothing_politely():
    ask = Ask.yes_no("Sure?", lambda: Result.success("did it"))
    assert "didn't do anything" in answer(ask, "no").message


def test_conflict_choices(work):
    (work / "a.txt").write_text("new")
    (work / "b").mkdir()
    (work / "b" / "a.txt").write_text("old")
    ask = run_line("copy a.txt to b").ask
    assert ask.hint == "replace / keep both / cancel"
    for reply, label in [("replace", "replace"), ("keep both", "keep both"), ("both", "keep both"),
                         ("keep both please", "keep both"), ("cancel", "cancel"), ("no", "cancel")]:
        assert ask.match(reply).label == label


# --- the terminal asks and listens --------------------------------------------


def feed(monkeypatch, replies):
    queue = iter(replies)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(queue))


def test_terminal_asks_then_acts(work, monkeypatch, capsys):
    (work / "a.txt").write_text("x")
    feed(monkeypatch, ["yes"])
    assert terminal.show(run_line("move a.txt to documents")) is False
    assert (work / "documents" / "a.txt").exists()
    assert "Moved a.txt" in capsys.readouterr().out


def test_terminal_asks_again_when_it_does_not_understand(work, monkeypatch, capsys):
    (work / "a.txt").write_text("x")
    feed(monkeypatch, ["banana", "yes"])
    terminal.show(run_line("move a.txt to documents"))
    assert "didn't catch that" in capsys.readouterr().out
    assert (work / "documents" / "a.txt").exists()


def test_terminal_gives_up_after_three_misses(work, monkeypatch):
    (work / "a.txt").write_text("x")
    feed(monkeypatch, ["??", "??", "??"])
    terminal.show(run_line("move a.txt to documents"))
    assert (work / "a.txt").exists()
    assert not (work / "documents").exists()


def test_terminal_ctrl_c_cancels(work, monkeypatch):
    (work / "a.txt").write_text("x")

    def interrupt(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", interrupt)
    terminal.show(run_line("move a.txt to documents"))
    assert (work / "a.txt").exists()


def test_terminal_passes_exit_through(monkeypatch):
    assert terminal.show(run_line("bye")) is True
