"""The Today page and ticking habits. These use the real "today", so every
habit here starts long ago and is due every day unless a test says otherwise."""
from datetime import timedelta

from gawi import db
from gawi.dates import today

from .conftest import add_habit, post

JSON = {"Accept": "application/json"}


def value_today(app, habit_id):
    with app.app_context():
        row = db.query_one(
            "SELECT value FROM checkins WHERE habit_id = ? AND day = ?", (habit_id, today().isoformat())
        )
        return row["value"] if row else None


def test_home_is_the_today_page(owner_client, app, owner_id):
    add_habit(app, owner_id, "Walk")
    page = owner_client.get("/").get_data(as_text=True)
    assert "Magandang" in page and "Walk" in page and "0</strong>/<span data-total>1" in page
    assert 'aria-current="page"' in page and "Let&#39;s start" in page


def test_no_habits_yet_shows_ideas(owner_client):
    page = owner_client.get("/").get_data(as_text=True)
    assert "Start with one small habit" in page


def test_tick_and_untick(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk")
    data = post(owner_client, f"/checkin/{habit_id}", {"action": "toggle"}, headers=JSON).get_json()
    assert data["done"] is True and data["value"] == 1
    assert data["summary"] == {"done": 1, "total": 1, "percent": 100, "message": "Perfect day! Ang galing mo! 🌅"}
    assert value_today(app, habit_id) == 1

    data = post(owner_client, f"/checkin/{habit_id}", {"action": "toggle"}, headers=JSON).get_json()
    assert data["done"] is False
    assert value_today(app, habit_id) is None  # not done = no row


def test_without_javascript_the_form_goes_back_home(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk")
    response = post(owner_client, f"/checkin/{habit_id}", {"action": "toggle"})
    assert response.status_code == 302 and response.headers["Location"] == f"/#habit-{habit_id}"
    assert value_today(app, habit_id) == 1


def test_count_up_and_down(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Water", kind="count", target=3, unit="glasses")
    for expected in (1, 2):
        data = post(owner_client, f"/checkin/{habit_id}", {"action": "plus"}, headers=JSON).get_json()
        assert data["value"] == expected and data["done"] is False
    assert data["line"] == "2 / 3 glasses" and data["percent"] == 67
    data = post(owner_client, f"/checkin/{habit_id}", {"action": "plus"}, headers=JSON).get_json()
    assert data["done"] is True
    post(owner_client, f"/checkin/{habit_id}", {"action": "minus"}, headers=JSON)
    assert value_today(app, habit_id) == 2


def test_minus_never_goes_below_zero(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Water", kind="count", target=3)
    data = post(owner_client, f"/checkin/{habit_id}", {"action": "minus"}, headers=JSON).get_json()
    assert data["value"] == 0 and value_today(app, habit_id) is None


def test_progress_counts_only_habits_for_today(owner_client, app, owner_id):
    add_habit(app, owner_id, "Walk", position=0)
    not_today = str(today().isoweekday() % 7 + 1)  # tomorrow's weekday number
    add_habit(app, owner_id, "Gym", schedule="weekdays", weekdays=not_today, position=1)
    future = (today() + timedelta(days=3)).isoformat()
    add_habit(app, owner_id, "Later", start_date=future, created_at=today().isoformat(), position=2)
    page = owner_client.get("/").get_data(as_text=True)
    assert "0</strong>/<span data-total>1" in page
    assert "Not for today (2)" in page


def test_a_habit_cannot_be_ticked_before_it_starts(owner_client, app, owner_id):
    future = (today() + timedelta(days=3)).isoformat()
    habit_id = add_habit(app, owner_id, "Later", start_date=future)
    assert post(owner_client, f"/checkin/{habit_id}", {"action": "toggle"}).status_code == 400


def test_archived_and_other_peoples_habits_cannot_be_ticked(owner_client, app, owner_id, other_id):
    archived = add_habit(app, owner_id, "Old", archived_at="2026-10-01")
    pedros = add_habit(app, other_id, "Pedro's")
    assert post(owner_client, f"/checkin/{archived}", {"action": "toggle"}).status_code == 404
    assert post(owner_client, f"/checkin/{pedros}", {"action": "toggle"}).status_code == 404
    assert value_today(app, pedros) is None


def test_unknown_action(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk")
    assert post(owner_client, f"/checkin/{habit_id}", {"action": "explode"}).status_code == 400


def test_the_demo_badge_replaces_the_banner(client):
    post(client, "/demo")
    page = client.get("/").get_data(as_text=True)
    assert 'class="demo-badge"' in page and "start fresh every hour" in page
    assert "demo-banner" not in page
