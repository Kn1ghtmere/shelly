from shelly.core.engine import run_line


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


def test_desktop_app_without_actions_rejects_extra_words(fake):
    result = run_line("open calculator play lofi")
    assert not result.ok
    assert "extra words" in result.message
    assert fake.apps == []


def test_browser_search(fake):
    result = run_line('open chrome search "ben 10"')
    assert result.ok
    assert fake.urls_in == [("chrome", "https://www.google.com/search?q=ben+10")]
    assert fake.apps == []


def test_browser_search_uses_the_right_name_per_os(fake):
    fake.key = "mac"
    run_line("open chrome search lofi")
    assert fake.urls_in[0][0] == "Google Chrome"


def test_every_browser_can_search(fake):
    for browser in ("firefox", "edge", "chrome"):
        assert run_line(f"open {browser} search lofi").ok
    assert len(fake.urls_in) == 3


def test_browser_unknown_action(fake):
    result = run_line("open firefox play lofi")
    assert not result.ok
    assert "search" in result.message


def test_plain_browser_still_just_launches(fake):
    run_line("open firefox")
    assert fake.apps == ["firefox"]
    assert fake.urls_in == []


def test_unknown_app_suggests_a_close_one(fake):
    result = run_line("open yotube")
    assert not result.ok
    assert "youtube" in result.message
    assert "add app" in result.message


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
    result = run_line("open youtube at 5")
    assert not result.ok
    assert "'at'" in result.message


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
    assert "firefox  - search" in result.message
