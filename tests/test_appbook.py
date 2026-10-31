import pytest

from shelly.core.appbook import DEFAULT_FILE, Action, AppBook, AppConfigError


@pytest.fixture
def book():
    return AppBook.load([DEFAULT_FILE])


def test_default_apps_load(book):
    youtube = book.find("youtube")
    assert youtube.kind == "web"
    assert set(youtube.actions) == {"search", "play"}


def test_aliases_and_case(book):
    assert book.find("YT").name == "youtube"


def test_desktop_app_names_differ_per_os(book):
    chrome = book.find("chrome")
    assert chrome.launch_name("windows") == "chrome"
    assert chrome.launch_name("mac") == "Google Chrome"
    assert book.find("firefox").launch_name("linux") == "firefox"


def test_query_is_url_encoded():
    action = Action("search", "https://x.test/?q={query}")
    assert action.build("ben 10 & friends") == "https://x.test/?q=ben+10+%26+friends"


def test_suggests_close_names(book):
    assert book.suggest("yotube") == "youtube"
    assert book.suggest("zzzzzz") is None


def test_user_file_overrides_and_adds(tmp_path):
    mine = tmp_path / "apps.toml"
    mine.write_text(
        '[youtube]\ntype = "web"\nhome = "https://mine.test"\n\n'
        '[notes]\ntype = "app"\nname = "obsidian"\n'
    )
    book = AppBook.load([DEFAULT_FILE, mine])
    assert book.find("youtube").home == "https://mine.test"
    assert book.find("notes").launch_name("windows") == "obsidian"
    assert book.find("google") is not None


def test_missing_user_file_is_fine(tmp_path):
    assert AppBook.load([DEFAULT_FILE, tmp_path / "nope.toml"]).find("youtube")


def test_broken_toml_names_the_file(tmp_path):
    bad = tmp_path / "apps.toml"
    bad.write_text("[youtube\n")
    with pytest.raises(AppConfigError, match="apps.toml"):
        AppBook.load([bad])


def test_web_app_needs_a_home(tmp_path):
    bad = tmp_path / "apps.toml"
    bad.write_text('[thing]\ntype = "web"\n')
    with pytest.raises(AppConfigError, match="home"):
        AppBook.load([bad])


def test_action_needs_a_url(tmp_path):
    bad = tmp_path / "apps.toml"
    bad.write_text('[thing]\ntype = "web"\nhome = "https://x.test"\n[thing.actions.go]\nnote = "hi"\n')
    with pytest.raises(AppConfigError, match="needs a url"):
        AppBook.load([bad])
