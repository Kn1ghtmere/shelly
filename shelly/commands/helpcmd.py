import difflib

from ..core.intent import Intent
from ..core.registry import command
from ..core.result import Result

# topic -> lines. Edit this to change what `help` says.
TOPICS: dict[str, list[str]] = {
    "go": [
        "Move around your folders.",
        "  go to downloads        go up        go home        go back        cd ..",
        "  go to tools in D:      go to tools in assets in D:      go to D:",
        "  where am i             (shows the folder you're in)",
    ],
    "list": [
        "See what's in a folder (folders first, 50 at a time).",
        "  list        list downloads        list in downloads        list tools in D:",
        "  more        (the next 50)          list all     (everything)",
    ],
    "make": [
        "Make folders and files.",
        "  make a folder called projects        make a folder called \"my stuff\"",
        "  make a file called notes.txt         make a file called todo.txt with \"buy milk\"",
        "  make a folder called x in documents in D:",
    ],
    "copy": [
        "Copy, cut, paste and move. Shelly never overwrites without asking.",
        "  copy notes.txt                 then:   paste      paste to downloads      paste here",
        "  copy a.txt and b.txt           (several things, joined with 'and')",
        "  cut notes.txt                  then paste: it moves",
        "  copy notes.txt to backup       move notes.txt to documents",
        "  copy report.txt in assets in D: to backup in E:",
        "If a folder is missing I'll offer to make it. If a name clashes: replace / keep both / cancel.",
    ],
    "rename": ["Change a name (not the place).", "  rename notes.txt to ideas.txt"],
    "delete": [
        "Delete things. They go to the trash, and I always ask first.",
        "  delete old.txt        delete a.txt and b.txt        remove old.txt",
    ],
    "show": [
        "Open your file explorer.",
        "  show                (this folder)        show notes.txt      (with the file highlighted)",
    ],
    "open": [
        "Open apps, websites, files and folders.",
        "  open youtube        open youtube search \"ben 10\"        open youtube play rickroll",
        "  open chrome search \"ben 10\"        open firefox        open notes.txt",
        "  open youtube in brave        open rythm using chrome        (a browser of your choice)",
        "  apps                (lists everything I know)",
    ],
    "add": [
        "Teach me your own apps and websites. I'll ask what kind it is and set up features like search.",
        "  add app \"C:\\Program Files\\Spotify\\spotify.exe\" as spotify",
        "  add website https://rythm.fm as rythm        remove app spotify",
    ],
    "close": ["Close a program politely (it asks about unsaved work).", "  close notepad        close notepad and calculator"],
    "music": [
        "Control whatever music is playing.",
        "  music play        music pause        music next        music previous        music vol 50",
        "  volume 30        (the whole computer's volume)",
    ],
    "and": [
        "Do several things in one line.",
        "  open youtube and open spotify          (both at once)",
        "  make a folder called x and then go to x    (one after the other; stops if one fails)",
        "'and' only splits when a command word follows it, so 'copy a and b' is one command.",
    ],
    "quotes": [
        "One word is one thing. Anything longer goes in quotes.",
        "  play rickroll        play \"outdoor boys\"        make a folder called \"my stuff\"",
        "Numbers (volume 50) and single words never need quotes.",
    ],
    "in": [
        "'in' says where something is, and you can chain it from the inside out.",
        "  go to tools in assets in D:       means  D:\\assets\\tools",
        "  open youtube in brave             (when brave is a browser)",
    ],
    "exit": ["Leave Shelly.", "  bye        goodbye        exit        quit        end"],
}

ALIASES = {
    "cd": "go", "goto": "go", "back": "go", "where": "go", "up": "go",
    "ls": "list", "more": "list", "all": "list",
    "mkdir": "make", "folder": "make", "file": "make", "mkfile": "make", "touch": "make",
    "cut": "copy", "paste": "copy", "move": "copy", "cp": "copy", "mv": "copy", "clipboard": "copy",
    "rm": "delete", "del": "delete", "trash": "delete", "remove": "delete",
    "apps": "open", "browser": "open", "browsers": "open", "using": "open",
    "volume": "music", "vol": "music", "pause": "music", "play": "music",
    "chain": "and", "then": "and", "chaining": "and", "quote": "quotes",
    "bye": "exit", "quit": "exit", "goodbye": "exit", "end": "exit",
}

OVERVIEW = """Here's what I can do. Type  help <topic>  for examples.

  go        move around            list      see what's in a folder
  make      folders and files      copy      copy, cut, paste, move
  rename    change a name          delete    to the trash, after asking
  show      open the file explorer open      apps, websites, files
  add       teach me an app        close     close a program
  music     play, pause, volume    and       several commands in one line
  quotes    when to use "quotes"   in        'tools in assets in D:'

You can also just type things like:  go to downloads   /   make a folder called projects"""


@command("help", "?")
def help_command(intent: Intent) -> Result:
    if not intent.args:
        return Result.success(OVERVIEW)

    word = intent.args[0].lower()
    topic = word if word in TOPICS else ALIASES.get(word)
    if topic is None:
        guess = difflib.get_close_matches(word, [*TOPICS, *ALIASES], n=1, cutoff=0.6)
        if guess:
            topic = guess[0] if guess[0] in TOPICS else ALIASES[guess[0]]
        else:
            return Result.fail(f"I don't have help for '{word}'. Type help to see the topics.")
    return Result.success("\n".join(TOPICS[topic]))
