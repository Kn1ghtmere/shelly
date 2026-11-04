from dataclasses import dataclass, field

from .errors import ParseError


@dataclass(frozen=True)
class Token:
    text: str
    quoted: bool = False
    # Where the token sits in the original line (used to keep a command's own text).
    start: int = field(default=0, compare=False)
    end: int = field(default=0, compare=False)


def tokenize(line: str) -> list[Token]:
    """Split a line into words. "double" or 'single' quotes keep words together.

    A quote only opens at the start of a word, so apostrophes like in
    "what's" stay as normal characters. Backslashes are left alone, so
    Windows paths work without any escaping.
    """
    tokens: list[Token] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch.isspace():
            i += 1
        elif ch in "\"'":
            end = line.find(ch, i + 1)
            if end == -1:
                raise ParseError(f"There's an opening {ch} quote with no closing one.")
            tokens.append(Token(line[i + 1:end], True, i, end + 1))
            i = end + 1
        else:
            j = i
            while j < n and not line[j].isspace():
                j += 1
            tokens.append(Token(line[i:j], False, i, j))
            i = j
    return tokens
