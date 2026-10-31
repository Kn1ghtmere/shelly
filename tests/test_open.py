import pytest

from shelly import commands  # noqa: F401
from shelly import platform as plat
from shelly.core import appbook
from shelly.core.engine import run_line


class FakePlatform(plat.Platform):
    key = "windows"

    def __init__(self):
        self.urls, self.apps, self.paths = [], [], []
        self.error = None

    def _maybe_fail(self):
        if self.error:
            raise plat.PlatformError(self.error)

    def open_url(self, url):
        self._maybe_fail()
        self.urls.append(url)

    def open_app(self, name):
        self._maybe_fail()
        self.apps.append(name)

    def open_path(self, path):
        self._maybe_fail()
        self.paths.append(path)


@pytest.fixture
def fake():
    system = FakePlatform()
    plat.set_current(system)
    appbook.set_book(appbook.AppBook.load([appbook.DEFAULT_FILE]))
    yield system
    plat.set_current(None)
    appbook.set_book(None)


def test_open_web_app_opens_home(fake):
    assert run_line("open youtube").ok
    assert fake.urls == ["https://www.youtube.com"]


def test_alias_works(fake):
    run_line("open yt")
    assert fake.urls == ["https://www.youtube.com"]


def test_search_with_quoted_query(fake):
    result = run_line('open youtube search "ben 10"')
    assert result.ok
    assert fake.urls == ["https://www.youtube.com/results?search_query=ben+10"]


def test_play_with_single_word_needs_no_quotes(fake):
    result = run_line("open youtube play rickroll")
    assert result.ok
    assert "rickroll" in fake.urls[0]
    assert "Auto-playing" in result.message


def test_search_without_query_explains(fake):
    result = run_line("open youtube search")
    assert not result.ok
    assert 'open youtube search "something"' in result.message
    assert fake.urls == []


def test_unquoted_multi_word_query_suggests_quotes(fake):
    result = run_line("open youtube play ben 10")
    assert not result.ok
    assert 'open youtube play "ben 10"' in result.message
    assert fake.urls == []


def test_unknown_action_lists_the_real_ones(fake):
    result = run_line('open youtube dance "x"')
    assert not result.ok
    assert "play, search" in result.message


def test_desktop_app_uses_platform_name(fake):
    run_line("open chrome")
    fake.key = "mac"
    run_line("open chrome")
    assert fake.apps == ["chrome", "Google Chrome"]


def test_desktop_app_rejects_extra_words(fake):
    result = run_line("open firefox play lofi")
    assert not result.ok
    assert fake.apps == []


def test_unknown_app_suggests_a_close_one(fake):
    result = run_line("open yotube")
    assert not result.ok
    assert "youtube" in result.message


def test_existing_file_opens_with_default_program(fake, tmp_path):
    note = tmp_path / "notes.txt"
    note.write_text("hi")
    assert run_line(f'open "{note}"').ok
    assert fake.paths == [note]


def test_volume_is_noted_but_not_faked(fake):
    result = run_line("open youtube volume 50")
    assert result.ok
    assert "volume 50" in result.message
    assert "isn't built yet" in result.message


def test_other_options_are_rejected(fake):
    result = run_line("open youtube in downloads")
    assert not result.ok
    assert "'in'" in result.message


def test_open_alone_explains(fake):
    assert not run_line("open").ok


def test_platform_errors_become_friendly_results(fake):
    fake.error = "I couldn't open a web browser."
    result = run_line("open youtube")
    assert not result.ok
    assert "browser" in result.message


def test_apps_command_lists_known_apps(fake):
    result = run_line("apps")
    assert result.ok
    assert "youtube (yt)" in result.message
    assert "firefox" in result.message
