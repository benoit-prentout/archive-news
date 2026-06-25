from newsletter_archive import config

def test_defaults_and_env_override(monkeypatch):
    monkeypatch.setenv("ARCHIVE_GMAIL_USER", "me@example.com")
    monkeypatch.setenv("ARCHIVE_TARGET_LABEL", "X/labels")
    s = config.Settings()
    assert s.gmail_user == "me@example.com"
    assert s.target_label == "X/labels"
    assert s.db_path == "archive.db"
    assert s.image_workers == 5
    assert s.redirect_workers == 10
    assert s.http_timeout == 15
    assert "Mozilla" in s.user_agent
