import pytest

from shelly.core import appbook
from shelly.core.engine import run_line
from shelly.platform.linux import LinuxPlatform
from shelly.platform.base import PlatformError


@pytest.fixture
def exe(tmp_path):
    path = tmp_path / "Cool App.exe"
    path.write_text("not really a program")
    return path


def test_add_app_then_open_it(fake, exe):
    result = run_line(f'add app "{exe}" as cool')
    assert result.ok
    assert run_line("open cool").ok
    assert fake.apps == [str(exe.resolve())]


def test_name_defaults_to_the_filename(fake, exe):
    assert run_line(f'add app "{exe}"').ok
    assert appbook.get_book().find("cool-app")


def test_add_app_that_does_not_exist(fake):
    result = run_line('add app "C:\\nope\\nothing.exe" as nothing')
    assert not result.ok
    assert "can't find" in result.message


def test_adding_twice_is_refused(fake, exe):
    run_line(f'add app "{exe}" as cool')
    result = run_line(f'add app "{exe}" as cool')
    assert not result.ok
    assert "remove app cool" in result.message


def test_replacing_a_builtin_says_so(fake, exe):
    result = run_line(f'add app "{exe}" as chrome')
    assert result.ok
    assert "replaces the built-in" in result.message
    run_line("open chrome")
    assert fake.apps == [str(exe.resolve())]


def test_paths_with_apostrophes_survive(fake, tmp_path):
    odd = tmp_path / "it's here.exe"
    odd.write_text("x")
    assert run_line(f'add app "{odd}" as odd').ok
    assert run_line("open odd").ok
    assert fake.apps == [str(odd.resolve())]


def test_add_website(fake):
    assert run_line("add website https://example.com as example").ok
    run_line("open example")
    assert fake.urls == ["https://example.com"]


def test_add_website_without_scheme(fake):
    assert run_line("add website example.org").ok
    run_line("open example")
    assert fake.urls == ["https://example.org"]


def test_add_with_bad_usage(fake):
    assert "Try: add app" in run_line("add").message
    assert "Try: add app" in run_line("add thing").message


def test_add_with_spaces_needs_quotes(fake):
    result = run_line("add app my program.exe")
    assert not result.ok
    assert '"my program.exe"' in result.message


def test_bad_names_are_refused(fake, exe):
    assert not run_line(f'add app "{exe}" as "a.b"').ok


def test_remove_app(fake, exe):
    run_line(f'add app "{exe}" as cool')
    assert run_line("remove app cool").ok
    assert not run_line("open cool").ok


def test_remove_keeps_other_apps(fake, exe, tmp_path):
    other = tmp_path / "other.exe"
    other.write_text("x")
    run_line(f'add app "{exe}" as cool')
    run_line(f'add app "{other}" as other')
    run_line("remove app cool")
    assert run_line("open other").ok
    assert not run_line("open cool").ok


def test_cannot_remove_builtin_apps(fake):
    result = run_line("remove app youtube")
    assert not result.ok
    assert "built in" in result.message


def test_remove_unknown_app(fake):
    assert not run_line("remove app zzz").ok


def test_remove_usage(fake):
    assert "Try: remove app" in run_line("remove thing").message


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
