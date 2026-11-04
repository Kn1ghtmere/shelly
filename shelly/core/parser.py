from dataclasses import dataclass

from . import registry
from .aliases import ALIASES, LEADING_POLITE, OPTION_KEYWORDS, TRAILING_POLITE
from .errors import ParseError
from .intent import Intent
from .nodes import Block, Line, Node
from .tokenizer import Token, tokenize

BLOCK_OPENERS = {"if", "repeat", "for", "define"}


@dataclass
class Chain:
    """Commands joined by 'and' / 'and then'.

    Each stage runs after the one before it ('and then'). Inside a stage the
    commands run at the same time ('and')."""

    stages: list[list[Intent]]


def parse_line(
    line: str,
    *,
    aliases: dict[str, str] = ALIASES,
    option_keywords: set[str] = OPTION_KEYWORDS,
    line_number: int | None = None,
) -> Intent:
    """Turn one command's text into an Intent."""
    try:
        return parse_tokens(
            tokenize(line), line.strip(),
            aliases=aliases, option_keywords=option_keywords, line_number=line_number,
        )
    except ParseError as error:
        if error.line_number is None:
            error.line_number = line_number
        raise


def parse_tokens(
    tokens: list[Token],
    raw: str,
    *,
    aliases: dict[str, str] = ALIASES,
    option_keywords: set[str] = OPTION_KEYWORDS,
    line_number: int | None = None,
) -> Intent:
    tokens = _strip_polite(tokens)
    if not tokens:
        raise ParseError("Tell me what to do, for example: open firefox")
    tokens = _apply_aliases(tokens, aliases)
    args, options, containers = _split_options(tokens[1:], option_keywords)
    return Intent(
        verb=tokens[0].text.lower(),
        args=args,
        options=options,
        raw=raw,
        line_number=line_number,
        containers=containers,
    )


def parse_chain(
    line: str,
    *,
    aliases: dict[str, str] = ALIASES,
    option_keywords: set[str] = OPTION_KEYWORDS,
    is_command=None,
) -> Chain:
    """Split a line at 'and then' (always) and at 'and' (only when a real
    command follows, so 'copy a and b' and 'play rock and roll' stay whole)."""
    tokens = tokenize(line)
    if not tokens:
        return Chain([])
    check = is_command or (lambda rest: _is_known_command(rest, aliases))

    stages: list[list[Intent]] = []
    for separator, group in _split_segments(tokens, check):
        raw = line[group[0].start:group[-1].end]
        intent = parse_tokens(group, raw, aliases=aliases, option_keywords=option_keywords)
        if separator == "and" and stages:
            stages[-1].append(intent)
        else:
            stages.append([intent])
    return Chain(stages)


def parse_script(text: str) -> list[Node]:
    """Turn a whole script into a list of Lines and Blocks."""
    root: list[Node] = []
    stack: list[Block] = []

    def current() -> list[Node]:
        if not stack:
            return root
        block = stack[-1]
        return block.else_body if block.in_else else block.body

    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        intent = parse_line(line, line_number=number)

        if intent.verb in BLOCK_OPENERS:
            block = Block(header=intent)
            current().append(block)
            stack.append(block)
        elif intent.verb == "else":
            if not stack or stack[-1].header.verb != "if":
                raise ParseError("'else' only belongs inside an 'if'.", number)
            if stack[-1].in_else:
                raise ParseError("This 'if' already has an 'else'.", number)
            stack[-1].in_else = True
        elif intent.verb == "end":
            if not stack:
                raise ParseError("'end' doesn't close anything.", number)
            stack.pop()
        else:
            current().append(Line(intent))

    if stack:
        opener = stack[-1].header
        raise ParseError(
            f"'{opener.verb}' never ends. Add an 'end' after it.", opener.line_number
        )
    return root


# --- helpers -----------------------------------------------------------


def _is_word(token: Token, words: set[str]) -> bool:
    # Quoted text is never a keyword, so quotes are the escape hatch.
    return not token.quoted and token.text.lower() in words


def _strip_polite(tokens: list[Token]) -> list[Token]:
    start, end = 0, len(tokens)
    while start < end and _is_word(tokens[start], LEADING_POLITE):
        start += 1
    while end > start and _is_word(tokens[end - 1], TRAILING_POLITE):
        end -= 1
    return tokens[start:end]


def _match_alias(tokens: list[Token], aliases: dict[str, str]) -> tuple[int, str] | None:
    phrases = sorted(
        ((tuple(p.lower().split()), verb) for p, verb in aliases.items()),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for words, verb in phrases:
        size = len(words)
        if len(tokens) >= size and all(
            not t.quoted and t.text.lower() == w for t, w in zip(tokens, words)
        ):
            return size, verb
    return None


def _apply_aliases(tokens: list[Token], aliases: dict[str, str]) -> list[Token]:
    hit = _match_alias(tokens, aliases)
    if hit is None:
        return tokens
    size, verb = hit
    return [Token(verb)] + tokens[size:]


def _is_known_command(rest: list[Token], aliases: dict[str, str]) -> bool:
    rest = _strip_polite(rest)
    if not rest or rest[0].quoted:
        return False
    return _match_alias(rest, aliases) is not None or registry.find(rest[0].text) is not None


def _split_segments(tokens: list[Token], is_command) -> list[tuple[str, list[Token]]]:
    segments: list[tuple[str, list[Token]]] = []
    current: list[Token] = []
    separator = "start"
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if current and _is_word(token, {"and"}):
            j = i + 1
            then = j < len(tokens) and _is_word(tokens[j], {"then"})
            k = j + 1 if then else j
            if then and k >= len(tokens):
                raise ParseError("'and then' needs another command after it.")
            if k < len(tokens) and (then or is_command(tokens[k:])):
                segments.append((separator, current))
                current, separator, i = [], ("then" if then else "and"), k
                continue
        current.append(token)
        i += 1
    segments.append((separator, current))
    return segments


def _split_options(
    tokens: list[Token], keywords: set[str]
) -> tuple[list[str], dict[str, str], dict[str, list[str]]]:
    args: list[str] = []
    options: dict[str, str] = {}
    containers: dict[str, list[str]] = {}
    current: str | None = None
    values: list[str] = []
    owner = ""  # what an 'in' belongs to: the args, or the last option before it

    def flush() -> None:
        if current is None:
            return
        if not values:
            raise ParseError(
                f"'{current}' needs something after it. "
                f"(If it's part of what you're typing, put it in quotes.)"
            )
        if len(values) > 1:
            joined = " ".join(values)
            raise ParseError(
                f"'{current}' takes one thing, but I got {len(values)} words: {joined}. "
                f'If it\'s one thing, put it in quotes: {current} "{joined}"'
            )
        options[current] = values[0]
        if current == "in":
            containers.setdefault(owner, []).append(values[0])

    for token in tokens:
        if _is_word(token, keywords):
            flush()
            current = token.text.lower()
            values = []
            if current != "in":
                owner = current
        elif current is None:
            args.append(token.text)
        else:
            values.append(token.text)
    flush()
    return args, options, containers
