import pytest

from shelly.core.errors import ParseError
from shelly.core.tokenizer import Token, tokenize


def texts(line):
    return [t.text for t in tokenize(line)]


def test_splits_on_whitespace():
    assert texts("  open   firefox ") == ["open", "firefox"]


def test_double_quotes_group_words():
    assert tokenize('say "hello world"') == [Token("say"), Token("hello world", True)]


def test_single_quotes_group_words():
    assert texts("say 'hello world'") == ["say", "hello world"]


def test_apostrophe_inside_word_is_not_a_quote():
    assert texts("what's in here") == ["what's", "in", "here"]


def test_backslashes_survive():
    assert texts(r"go to C:\Users\me") == ["go", "to", r"C:\Users\me"]


def test_unclosed_quote_is_an_error():
    with pytest.raises(ParseError):
        tokenize('say "hello')


def test_empty_line_gives_no_tokens():
    assert tokenize("   ") == []
