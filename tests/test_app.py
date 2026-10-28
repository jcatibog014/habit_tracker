import re
from pathlib import Path

import pytest

from gawi import create_app, db

TEMPLATES = Path(__file__).parent.parent / "gawi" / "templates"


def test_health_check_needs_no_login(client):
    response = client.get("/healthz")
    assert response.status_code == 200 and response.get_json() == {"status": "ok"}


def test_security_headers(client):
    response = client.get("/login")
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_no_inline_scripts():
    """The CSP blocks inline <script> code, so no template may have any."""
    for template in TEMPLATES.glob("*.html"):
        for tag in re.findall(r"<script[^>]*>", template.read_text(encoding="utf-8")):
            assert "src=" in tag or 'type="application/json"' in tag, f"{template.name}: {tag}"


def test_unknown_page_is_a_friendly_404(owner_client):
    response = owner_client.get("/nope")
    assert response.status_code == 404
    assert "couldn&#39;t find that page" in response.get_data(as_text=True)


def test_every_page_has_the_logo_and_tabs(owner_client):
    page = owner_client.get("/habits").get_data(as_text=True)
    assert 'class="logo"' in page and 'aria-current="page"' in page and "Settings" in page


def test_the_emoji_font_has_every_icon(client):
    from urllib.parse import unquote

    from gawi import EMOJI_FONT_URL
    from gawi.validation import ICONS
    text = unquote(EMOJI_FONT_URL.split("text=")[1])
    assert all(icon in text for icon in ICONS)
    assert EMOJI_FONT_URL in client.get("/login").get_data(as_text=True).replace("&amp;", "&")


def test_on_render_a_real_secret_key_and_database_are_needed(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app()
    monkeypatch.setenv("SECRET_KEY", "a real one")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        create_app()


def test_upgrade_db_on_a_new_database_does_nothing(app):
    with app.app_context():
        assert db.upgrade_db() == (len(db.MIGRATIONS), len(db.MIGRATIONS))


def test_one_check_in_per_habit_per_day(app, owner_id):
    from .conftest import add_habit
    habit_id = add_habit(app, owner_id)
    with app.app_context():
        db.execute("INSERT INTO checkins (habit_id, day, value) VALUES (?, '2026-10-02', 1)", (habit_id,))
        with pytest.raises(Exception):
            db.execute("INSERT INTO checkins (habit_id, day, value) VALUES (?, '2026-10-02', 1)", (habit_id,))
