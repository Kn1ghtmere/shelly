import pytest

from shelly.core.errors import ParseError
from shelly.core.parser import parse_line

CASES = [
    # (line, verb, args, options)
    ("open youtube play outdoor boys volume 50",
     "open", ["youtube", "play", "outdoor", "boys"], {"volume": "50"}),
    ("OPEN YouTube", "open", ["YouTube"], {}),
    ("open firefox", "open", ["firefox"], {}),
    ("please open firefox", "open", ["firefox"], {}),
    ("can you please open firefox", "open", ["firefox"], {}),
    ("open firefox please", "open", ["firefox"], {}),
    ("  hello   ", "hello", [], {}),
    # navigation
    ("go to downloads", "go", ["downloads"], {}),
    ("Go To Downloads", "go", ["Downloads"], {}),
    ("cd projects", "go", ["projects"], {}),
    ("go back", "back", [], {}),
    ("where am i", "where", [], {}),
    ("pwd", "where", [], {}),
    (r"go to C:\Users\me", "go", [r"C:\Users\me"], {}),
    # listing
    ("ls", "list", [], {}),
    ("show files", "list", [], {}),
    ("what's in here", "list", [], {}),
    ("show me what's in here", "list", [], {}),
    ("list files in downloads", "list", [], {"in": "downloads"}),
    # folders
    ("make a folder called projects", "mkdir", ["projects"], {}),
    ("make folder projects", "mkdir", ["projects"], {}),
    ("create a directory named stuff", "mkdir", ["stuff"], {}),
    ("create a folder named my stuff", "mkdir", ["my", "stuff"], {}),
    ('make a folder called "my stuff"', "mkdir", ["my stuff"], {}),
    # options
    ("move notes.txt to documents", "move", ["notes.txt"], {"to": "documents"}),
    ("copy a.txt to backup in documents", "copy", ["a.txt"],
     {"to": "backup", "in": "documents"}),
    ('set topic to "outdoor boys"', "set", ["topic"], {"to": "outdoor boys"}),
    ("open youtube volume 50", "open", ["youtube"], {"volume": "50"}),
    # plain queries
    ("play outdoor boys", "play", ["outdoor", "boys"], {}),
    ("play the weeknd", "play", ["the", "weeknd"], {}),
    ("say it's fine", "say", ["it's", "fine"], {}),
    # quotes protect words from being treated as keywords
    ('open youtube search "lost in translation"', "open",
     ["youtube", "search", "lost in translation"], {}),
    ("play 'back to black'", "play", ["back to black"], {}),
    ('say "hello world"', "say", ["hello world"], {}),
    # script-ish headers
    ("wait 3 seconds", "wait", ["3", "seconds"], {}),
    ("repeat 3 times", "repeat", ["3", "times"], {}),
    ("for each file in downloads", "for", ["each", "file"], {"in": "downloads"}),
    ("if file notes.txt exists", "if", ["file", "notes.txt", "exists"], {}),
]


@pytest.mark.parametrize("line, verb, args, options", CASES)
def test_parse_line(line, verb, args, options):
    intent = parse_line(line)
    assert intent.verb == verb
    assert intent.args == args
    assert intent.options == options


def test_unquoted_keyword_still_counts_as_a_keyword():
    # Why multi-word text needs quotes: 'in' is an option word.
    intent = parse_line("open youtube search lost in translation")
    assert intent.args == ["youtube", "search", "lost"]
    assert intent.options == {"in": "translation"}


def test_intent_helpers():
    intent = parse_line("open youtube play outdoor boys")
    assert intent.target == "youtube"
    assert intent.rest == ["play", "outdoor", "boys"]
    assert intent.text == "youtube play outdoor boys"


def test_raw_is_kept():
    assert parse_line("  open firefox ").raw == "open firefox"


def test_option_without_value_is_an_error():
    with pytest.raises(ParseError, match="needs something after it"):
        parse_line("open youtube volume")


def test_unclosed_quote_is_an_error():
    with pytest.raises(ParseError):
        parse_line('say "hello')


def test_only_politeness_is_an_error():
    with pytest.raises(ParseError):
        parse_line("please")


def test_custom_alias_table():
    intent = parse_line("yeet file.txt", aliases={"yeet": "delete"})
    assert intent.verb == "delete"
    assert intent.args == ["file.txt"]


def test_option_takes_exactly_one_thing():
    with pytest.raises(ParseError, match="takes one thing") as error:
        parse_line("set topic to outdoor boys")
    assert 'to "outdoor boys"' in str(error.value)


def test_quoted_option_value_is_one_thing():
    assert parse_line('open youtube play "outdoor boys" volume 50').options == {"volume": "50"}


def test_numbers_and_single_words_need_no_quotes():
    intent = parse_line("play rickroll volume 50")
    assert intent.args == ["rickroll"]
    assert intent.options == {"volume": "50"}
