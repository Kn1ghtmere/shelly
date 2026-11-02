"""Data tables for the parser. Add phrasings here, not in code."""

# Words that mark the start of an option. Everything after one (up to the
# next option word) is that option's value:  volume 50   in downloads
OPTION_KEYWORDS = {"volume", "in", "at", "to", "from", "into", "as", "with", "by"}

# Politeness we silently drop.
LEADING_POLITE = {"please", "kindly", "can", "could", "would", "you"}
TRAILING_POLITE = {"please", "kindly"}


def _make_phrases(nouns: tuple[str, ...], canonical: str) -> dict[str, str]:
    """make/create [a] <noun> [called|named]  ->  canonical verb"""
    phrases = {}
    for verb in ("make", "create"):
        for article in ("", "a"):
            for noun in nouns:
                for tail in ("", "called", "named"):
                    words = (verb, article, noun, tail)
                    phrases[" ".join(w for w in words if w)] = canonical
    return phrases


# phrase -> the one-word verb it means. Longest phrase wins.
ALIASES: dict[str, str] = {
    # navigation
    "go to": "go",
    "goto": "go",
    "go into": "go",
    "change directory": "go",
    "cd": "go",
    "go back": "back",
    "where am i": "where",
    "what folder am i in": "where",
    "pwd": "where",
    # listing
    "list": "list",
    "ls": "list",
    "dir": "list",
    "show files": "list",
    "list files": "list",
    "list everything": "list",
    "what's in here": "list",
    "whats in here": "list",
    "show me what's in here": "list",
    "show me whats in here": "list",
    "show what's in here": "list",
    # copy / move / rename
    "cp": "copy",
    "make a copy of": "copy",
    "mv": "move",
    "ren": "rename",
    # folders and files
    **_make_phrases(("folder", "directory"), "mkdir"),
    "mkdir": "mkdir",
    **_make_phrases(("file",), "mkfile"),
    "mkfile": "mkfile",
    "touch": "mkfile",
}
