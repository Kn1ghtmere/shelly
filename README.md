# Shelly

A beginner-friendly shell you talk to in plain English.

    python -m shelly        # start it
    python -m pytest        # run the tests

Needs Python 3.11+.

## Install on another device

### Linux (Fedora, Ubuntu, Debian)

Open your terminal app. On Fedora, install Git and pipx with:

    sudo dnf install git pipx

On Ubuntu or Debian, use:

    sudo apt update
    sudo apt install git pipx

If your distribution does not have a `pipx` package, follow the
[pipx installation instructions](https://pipx.pypa.io/stable/installation/).
Then run:

    pipx ensurepath

Close and reopen the terminal so it picks up the PATH update, then install and
start Shelly:

    pipx install "git+https://github.com/Kn1ghtmere/shelly.git"
    shelly

Hyprland is a desktop environment/window manager, not a Linux distribution, so
there are no Hyprland-specific install steps. Use the commands for the
distribution Hyprland is running on (for example, Fedora). These commands work
in common terminal shells such as Bash and Zsh.

### Other platforms

Install [pipx](https://pipx.pypa.io/) and Git, then run:

    pipx install "git+https://github.com/Kn1ghtmere/shelly.git"
    shelly

This installs Shelly in an isolated Python environment and adds the `shelly`
command to your PATH. After new changes are pushed, update with
`pipx upgrade shelly`. Your personal `.shelly/apps.toml` configuration is
separate and must be copied to the other device if you want to reuse it.

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
