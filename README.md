# Shelly

A beginner-friendly shell you talk to in plain English.

    python -m shelly        # start it
    python -m pytest        # run the tests

Needs Python 3.11+.

## How a line is read

    open youtube play "outdoor boys" volume 50
    ^verb ^-- args ----------------^  ^option^

The rule: **one word is one thing. Anything longer goes in quotes.**
Single words (`youtube`, `rickroll`) and numbers (`50`) never need quotes.

- The first word is the verb. Phrases like `go to` or `make a folder called`
  are aliases for one-word verbs (see `shelly/core/aliases.py`).
- Option words (`volume`, `in`, `to`, `at`, ...) take exactly one thing after
  them: `volume 50`, `in downloads`, `to "my backup"`.
- Quoted text is never treated as a keyword, so quotes also protect words
  like `in` and `to`: `play "back to black"`.
- Try `parse <any line>` to see how Shelly reads it.

## Scripts

Blocks (`if`, `repeat`, `for`, `define`) close with `end`. `else` is allowed
inside `if`. Lines starting with `#` are comments.
