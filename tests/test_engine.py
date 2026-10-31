from shelly import commands  # noqa: F401
from shelly.core.engine import run_line


def test_hello_works():
    result = run_line("hello")
    assert result.ok
    assert "Shelly" in result.message


def test_unknown_command_fails_politely():
    result = run_line("blorp")
    assert not result.ok
    assert "blorp" in result.message


def test_blank_line_does_nothing():
    assert run_line("   ") is None


def test_bye_requests_exit():
    assert run_line("bye").should_exit


def test_politeness_is_ignored():
    assert run_line("please hello").ok


def test_say_keeps_quoted_text():
    assert run_line('say "hello  world"').message == "hello  world"


def test_parse_error_becomes_a_failed_result():
    result = run_line('say "oops')
    assert not result.ok
    assert "quote" in result.message


def test_parse_command_shows_the_breakdown():
    result = run_line("parse open youtube play outdoor boys volume 50")
    assert result.ok
    assert "'volume': '50'" in result.message
    assert "open" in result.message
