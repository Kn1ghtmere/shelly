import pytest

from shelly.core.errors import ParseError
from shelly.core.nodes import Block, Line
from shelly.core.parser import parse_script


def test_plain_lines_comments_and_blanks():
    nodes = parse_script("# a comment\nhello\n\nsay hi\n")
    assert [type(n) for n in nodes] == [Line, Line]
    assert nodes[1].intent.verb == "say"


def test_block_collects_its_body():
    nodes = parse_script("repeat 3 times\n    say hello\nend\nsay done")
    assert isinstance(nodes[0], Block)
    assert nodes[0].header.verb == "repeat"
    assert [n.intent.verb for n in nodes[0].body] == ["say"]
    assert nodes[1].intent.verb == "say"


def test_nested_blocks():
    script = "for each file in downloads\n  if file a.txt exists\n    say hi\n  end\nend"
    outer = parse_script(script)[0]
    inner = outer.body[0]
    assert isinstance(inner, Block)
    assert inner.header.verb == "if"
    assert inner.body[0].intent.verb == "say"


def test_if_else():
    block = parse_script("if file a.txt exists\n say yes\nelse\n say no\nend")[0]
    assert block.body[0].intent.text == "yes"
    assert block.else_body[0].intent.text == "no"


def test_define_block():
    block = parse_script("define morning\n open youtube\nend")[0]
    assert block.header.verb == "define"
    assert block.header.args == ["morning"]


def test_missing_end_points_at_the_opener():
    with pytest.raises(ParseError, match="Line 2.*never ends"):
        parse_script("say hi\nrepeat 3 times\n say hi")


def test_stray_end():
    with pytest.raises(ParseError, match="Line 1"):
        parse_script("end")


def test_else_outside_if():
    with pytest.raises(ParseError, match="else"):
        parse_script("repeat 2 times\nelse\nend")


def test_double_else():
    with pytest.raises(ParseError, match="already has"):
        parse_script("if x\nelse\nelse\nend")


def test_errors_inside_scripts_carry_the_line_number():
    with pytest.raises(ParseError, match="Line 3"):
        parse_script('say hi\nsay hi\nsay "oops')
