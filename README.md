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

## Opening things

    open youtube
    open youtube search "ben 10"
    open youtube play rickroll
    open firefox
    open "C:\\Users\\me\\notes.txt"
    apps                    # list everything Shelly knows

The app list is `shelly/data/apps.toml`. To add your own, create
`.shelly/apps.toml` in your home folder with the same format; your entries
win over the built-in ones.

Everything OS-specific lives in `shelly/platform/` (windows, mac, linux).
Commands never check which system they're on.

## Files and folders

    go to downloads         # also: go up, go home, go back, cd ..
    where am i
    list                    # or: list downloads / list in downloads
    make a folder called projects
    make a folder called "my stuff"
    copy notes.txt to backup
    move notes.txt to documents
    rename notes.txt to ideas.txt

- Names can be typed in any capitals, and friendly names (`downloads`,
  `desktop`, `documents`, ...) work from anywhere.
- Shelly never overwrites: if the target exists, it says so and stops.
- Your home folders, the folder you're standing in, and drive roots can't be
  moved or renamed by accident.
