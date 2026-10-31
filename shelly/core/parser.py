from .aliases import ALIASES, LEADING_POLITE, OPTION_KEYWORDS, TRAILING_POLITE
from .errors import ParseError
from .intent import Intent
from .nodes import Block, Line, Node
from .tokenizer import Token, tokenize

BLOCK_OPENERS = {"if", "repeat", "for", "define"}


def parse_line(
    line: str,
    *,
    aliases: dict[str, str] = ALIASES,
    option_keywords: set[str] = OPTION_KEYWORDS,
    line_number: int | None = None,
) -> Intent:
    """Turn one line of text into an Intent."""
    try:
        tokens = tokenize(line)
        tokens = _strip_polite(tokens)
        if not tokens:
            raise ParseError("Tell me what to do, for example: open firefox")
        tokens = _apply_aliases(tokens, aliases)
        args, options = _split_options(tokens[1:], option_keywords)
    except ParseError as error:
        if error.line_number is None:
            error.line_number = line_number
        raise

    return Intent(
        verb=tokens[0].text.lower(),
        args=args,
        options=options,
        raw=line.strip(),
        line_number=line_number,
    )


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


def _apply_aliases(tokens: list[Token], aliases: dict[str, str]) -> list[Token]:
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
            return [Token(verb)] + tokens[size:]
    return tokens


def _split_options(
    tokens: list[Token], keywords: set[str]
) -> tuple[list[str], dict[str, str]]:
    args: list[str] = []
    options: dict[str, str] = {}
    current: str | None = None
    values: list[str] = []

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

    for token in tokens:
        if _is_word(token, keywords):
            flush()
            current = token.text.lower()
            values = []
        elif current is None:
            args.append(token.text)
        else:
            values.append(token.text)
    flush()
    return args, options
