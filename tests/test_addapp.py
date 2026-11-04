import pytest

from shelly.core import appbook
from shelly.core.engine import answer, run_line
from shelly.platform.base import PlatformError
from shelly.platform.linux import LinuxPlatform


@pytest.fixture
def exe(tmp_path):
    path = tmp_path / "Cool App.exe"
    path.write_text("not really a program")
    return path


def add(line, *replies):
    """Run an 'add' line and answer each question Shelly asks. Returns the last result."""
    result = run_line(line)
    for reply in replies:
        assert result.ask is not None, f"expected a question, got: {result.message}"
        result = answer(result.ask, reply)
    return result


# --- apps ------------------------------------------------------------------------


def test_add_app_asks_for_a_type_first(fake, exe):
    result = run_line(f'add app "{exe}" as cool')
    assert result.ask is not None
    assert "choose an app type for cool" in result.ask.prompt
    assert "1. browser" in result.ask.prompt and "2. other app" in result.ask.prompt
    assert not appbook.USER_FILE.exists()  # nothing saved until it's answered


def test_add_other_app_then_open_it(fake, exe):
    assert add(f'add app "{exe}" as cool', "2").ok
    assert run_line("open cool").ok
    assert fake.apps == [str(exe.resolve())]


def test_type_answers_can_be_words(fake, exe):
    assert add(f'add app "{exe}" as one', "other").ok
    assert add(f'add app "{exe}" as two', "browser", "none").ok
    assert appbook.get_book().find("two").role == "browser"


def test_add_browser_with_search_engine(fake, exe):
    result = add(f'add app "{exe}" as brave', "1", "4")
    assert result.ok
    assert 'open brave search "something"' in result.message
    assert "open youtube in brave" in result.message
    brave = appbook.get_book().find("brave")
    assert brave.role == "browser"
    assert "search.brave.com" in brave.actions["search"].url


def test_add_browser_with_no_search(fake, exe):
    assert add(f'add app "{exe}" as brave', "1", "none").ok
    assert appbook.get_book().find("brave").actions == {}


def test_search_engine_can_be_named(fake, exe):
    add(f'add app "{exe}" as brave', "browser", "duckduckgo")
    assert "duckduckgo" in appbook.get_book().find("brave").actions["search"].url


def test_name_defaults_to_the_filename(fake, exe):
    assert add(f'add app "{exe}"', "2").ok
    assert appbook.get_book().find("cool-app")


def test_add_app_that_does_not_exist(fake):
    result = run_line('add app "C:\\nope\\nothing.exe" as nothing')
    assert not result.ok
    assert "can't find" in result.message


def test_adding_twice_is_refused_before_asking(fake, exe):
    add(f'add app "{exe}" as cool', "2")
    result = run_line(f'add app "{exe}" as cool')
    assert result.ask is None
    assert "remove app cool" in result.message


def test_replacing_a_builtin_says_so(fake, exe):
    result = add(f'add app "{exe}" as chrome', "2")
    assert "replaces the built-in" in result.message


def test_paths_with_apostrophes_survive(fake, tmp_path):
    odd = tmp_path / "it's here.exe"
    odd.write_text("x")
    assert add(f'add app "{odd}" as odd', "2").ok
    run_line("open odd")
    assert fake.apps == [str(odd.resolve())]


def test_bad_names_are_refused(fake, exe):
    assert run_line(f'add app "{exe}" as "a.b"').ask is None
    assert not run_line(f'add app "{exe}" as "two words"').ok


def test_add_with_bad_usage(fake):
    assert "Try: add app" in run_line("add").message
    assert "Try: add app" in run_line("add thing").message


def test_add_with_spaces_needs_quotes(fake):
    result = run_line("add app my program.exe")
    assert not result.ok
    assert '"my program.exe"' in result.message


# --- links ---------------------------------------------------------------------------


def test_add_website_with_search(fake):
    result = add("add website https://rythm.fm as rythm", "https://rythm.fm/find?q={query}")
    assert result.ok
    run_line('open rythm search "daft punk"')
    assert fake.urls == ["https://rythm.fm/find?q=daft+punk"]


def test_add_website_without_search(fake):
    assert add("add website https://example.com as example", "no").ok
    run_line("open example")
    assert fake.urls == ["https://example.com"]


def test_website_search_address_needs_the_placeholder(fake):
    result = run_line("add website https://example.com as example")
    again = answer(result.ask, "https://example.com/search")
    assert again.ask is not None
    assert "{query}" in again.ask.prompt
    assert answer(again.ask, "no").ok


def test_a_link_can_be_added_as_an_app(fake):
    assert add('add app "https://music.youtube.com" as ytmusic', "no").ok
    run_line("open ytmusic")
    assert fake.urls == ["https://music.youtube.com"]


def test_website_without_scheme(fake):
    assert add("add website example.org", "no").ok
    run_line("open example")
    assert fake.urls == ["https://example.org"]


# --- removing -------------------------------------------------------------------------


def test_remove_app(fake, exe):
    add(f'add app "{exe}" as cool', "2")
    assert run_line("remove app cool").ok
    assert not run_line("open cool").ok


def test_remove_keeps_other_apps(fake, exe, tmp_path):
    other = tmp_path / "other.exe"
    other.write_text("x")
    add(f'add app "{exe}" as cool', "2")
    add(f'add app "{other}" as other', "2")
    run_line("remove app cool")
    assert run_line("open other").ok
    assert not run_line("open cool").ok


def test_removing_a_browser_with_search_takes_its_actions_too(fake, exe):
    add(f'add app "{exe}" as brave', "1", "1")
    assert run_line("remove app brave").ok
    assert appbook.get_book().find("brave") is None
    assert "brave" not in appbook.USER_FILE.read_text()


def test_cannot_remove_builtin_apps(fake):
    result = run_line("remove app youtube")
    assert not result.ok
    assert "built in" in result.message


def test_remove_unknown_app(fake):
    assert not run_line("remove app zzz").ok


def test_remove_something_else_is_delete(work):
    (work / "a.txt").write_text("x")
    result = run_line("remove a.txt")
    assert "to the trash" in result.ask.prompt


def test_removing_takes_sub_tables_with_it(tmp_path):
    file = tmp_path / "apps.toml"
    file.write_text(
        '[a]\ntype = "web"\nhome = "https://a.test"\n\n'
        '[a.actions]\nsearch = "https://a.test/?q={query}"\n\n'
        '[b]\ntype = "app"\nname = "bee"\n'
    )
    assert appbook.remove_user_section("a", file)
    book = appbook.AppBook.load([file])
    assert book.find("a") is None
    assert book.find("b") is not None


def test_remove_from_missing_file(tmp_path):
    assert not appbook.remove_user_section("a", tmp_path / "nope.toml")


def test_linux_open_url_in_missing_browser_is_a_friendly_error():
    with pytest.raises(PlatformError):
        LinuxPlatform().open_url_in("definitely-not-installed-xyz", "https://x.test")
