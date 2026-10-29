"""The habit page, fixing past days, rest days, habits to avoid, milestones,
quotes, installing on a phone, the database upgrade and the demo history."""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from gawi import auth, db, seed, streaks
from gawi.dates import today
from gawi.messages import QUOTES, quote_of_the_day

from .conftest import HABIT_FORM, add_habit, get_habit, post

JSON = {"Accept": "application/json"}
FIXTURES = Path(__file__).parent / "fixtures"


def entry(app, habit_id, day):
    with app.app_context():
        row = db.query_one("SELECT value, skipped FROM checkins WHERE habit_id = ? AND day = ?",
                           (habit_id, day.isoformat()))
        return (row["value"], row["skipped"]) if row else None


def tick_days(app, habit_id, first_back, last_back):
    """Mark the habit done from `first_back` days ago to `last_back` days ago."""
    with app.app_context():
        db.execute_many(
            "INSERT INTO checkins (habit_id, day, value) VALUES (?, ?, 1)",
            [(habit_id, (today() - timedelta(days=back)).isoformat()) for back in range(last_back, first_back + 1)],
        )
        db.commit()


# ---------- Past days and rest days ----------

def test_fix_a_past_day(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk")
    yesterday = today() - timedelta(days=1)
    response = post(owner_client, f"/checkin/{habit_id}", {"action": "toggle", "day": yesterday.isoformat()})
    assert response.status_code == 302
    assert entry(app, habit_id, yesterday) == (1, 0)


def test_future_days_and_days_before_the_start_are_refused(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk", start_date=(today() - timedelta(days=3)).isoformat())
    tomorrow = (today() + timedelta(days=1)).isoformat()
    long_ago = (today() - timedelta(days=10)).isoformat()
    assert post(owner_client, f"/checkin/{habit_id}", {"action": "toggle", "day": tomorrow}).status_code == 400
    assert post(owner_client, f"/checkin/{habit_id}", {"action": "toggle", "day": long_ago}).status_code == 400


def test_rest_day_on_and_off(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk")
    data = post(owner_client, f"/checkin/{habit_id}", {"action": "rest"}, headers=JSON).get_json()
    assert data["rested"] and data["line"] == "Rest day" and data["summary"]["total"] == 0
    assert entry(app, habit_id, today()) == (0, 1)
    post(owner_client, f"/checkin/{habit_id}", {"action": "rest"}, headers=JSON)
    assert entry(app, habit_id, today()) is None


def test_ticking_a_rest_day_ends_the_rest(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk")
    post(owner_client, f"/checkin/{habit_id}", {"action": "rest"}, headers=JSON)
    data = post(owner_client, f"/checkin/{habit_id}", {"action": "toggle"}, headers=JSON).get_json()
    assert data["done"] and not data["rested"]
    assert entry(app, habit_id, today()) == (1, 0)


def test_the_calendar_cycles_done_rest_not_done(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk")
    day = (today() - timedelta(days=2)).isoformat()
    form = {"action": "cycle", "day": day, "next": f"/habits/{habit_id}#calendar"}
    response = post(owner_client, f"/checkin/{habit_id}", form)
    assert response.headers["Location"] == f"/habits/{habit_id}#calendar"
    assert entry(app, habit_id, date.fromisoformat(day)) == (1, 0)
    post(owner_client, f"/checkin/{habit_id}", form)
    assert entry(app, habit_id, date.fromisoformat(day)) == (0, 1)
    post(owner_client, f"/checkin/{habit_id}", form)
    assert entry(app, habit_id, date.fromisoformat(day)) is None


# ---------- Habits to avoid ----------

def test_add_a_habit_to_avoid(owner_client, app, owner_id):
    post(owner_client, "/habits/new", {**HABIT_FORM, "name": "No soda", "kind": "avoid", "target": "9"})
    with app.app_context():
        soda = db.query_one("SELECT * FROM habits WHERE name = 'No soda'")
    assert (soda["kind"], soda["avoid"], soda["target"]) == ("check", 1, 1)
    page = owner_client.get(f"/habits/{soda['id']}/edit").get_data(as_text=True)
    assert 'value="avoid" checked' in page


def test_a_slip_and_taking_it_back(owner_client, app, owner_id):
    soda = add_habit(app, owner_id, "No soda", avoid=1)
    page = owner_client.get("/").get_data(as_text=True)
    assert "Clean today" in page and "1</strong>/<span data-total>1" in page
    data = post(owner_client, f"/checkin/{soda}", {"action": "toggle"}, headers=JSON).get_json()
    assert data["slipped"] and not data["done"] and data["summary"]["done"] == 0
    data = post(owner_client, f"/checkin/{soda}", {"action": "toggle"}, headers=JSON).get_json()
    assert not data["slipped"] and data["done"]


# ---------- Streaks, nudges and milestones ----------

def test_today_shows_the_streak_and_a_nudge(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk", start_date=(today() - timedelta(days=20)).isoformat())
    tick_days(app, habit_id, 5, 1)  # the 5 days before today
    page = owner_client.get("/").get_data(as_text=True)
    assert '<span data-streak-count>5</span>' in page and "5-day streak. Keep it going!" in page


def test_reaching_a_milestone_is_celebrated(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk", start_date=(today() - timedelta(days=20)).isoformat())
    tick_days(app, habit_id, 6, 1)  # 6 days in a row; today makes 7
    data = post(owner_client, f"/checkin/{habit_id}", {"action": "toggle"}, headers=JSON).get_json()
    assert data["streak"] == 7
    assert data["milestone"] == {"count": 7, "unit": "days", "message": "7 days of Walk. Ang galing!"}
    # Unticking goes back to 6: no celebration for that.
    data = post(owner_client, f"/checkin/{habit_id}", {"action": "toggle"}, headers=JSON).get_json()
    assert data["streak"] == 6 and data["milestone"] is None


def test_without_javascript_a_milestone_is_a_message(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk", start_date=(today() - timedelta(days=20)).isoformat())
    tick_days(app, habit_id, 6, 1)
    post(owner_client, f"/checkin/{habit_id}", {"action": "toggle"})
    assert "7 days of Walk" in owner_client.get("/").get_data(as_text=True)


# ---------- The habit page ----------

def test_the_habit_page(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk", start_date=(today() - timedelta(days=40)).isoformat())
    tick_days(app, habit_id, 34, 1)
    page = owner_client.get(f"/habits/{habit_id}").get_data(as_text=True)
    assert "Current streak" in page and "Longest streak" in page and "Milestones" in page
    assert page.count('class="badge is-earned') == 2  # 7 and 30
    assert "66 days to go" in page  # to 100
    assert "heatmap-grid" in page and "Show as table" in page and 'id="calendar"' in page


def test_the_habit_page_months(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk")
    this_month = today().strftime("%B %Y")
    assert this_month in owner_client.get(f"/habits/{habit_id}?month=nonsense").get_data(as_text=True)
    assert this_month in owner_client.get(f"/habits/{habit_id}?month=2999-01").get_data(as_text=True)


def test_nobody_sees_another_users_habit_page(owner_client, app, other_id):
    habit_id = add_habit(app, other_id, "Pedro's")
    assert owner_client.get(f"/habits/{habit_id}").status_code == 404
    day = (today() - timedelta(days=1)).isoformat()
    assert post(owner_client, f"/checkin/{habit_id}", {"action": "cycle", "day": day}).status_code == 404


def test_the_list_opens_the_habit_page(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk")
    page = owner_client.get("/habits").get_data(as_text=True)
    assert f'class="habit-main" href="/habits/{habit_id}"' in page


def test_saving_a_habit_goes_to_its_page(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Walk")
    response = post(owner_client, f"/habits/{habit_id}/edit", {**HABIT_FORM, "name": "Walk"})
    assert response.headers["Location"] == f"/habits/{habit_id}"


# ---------- Quotes ----------

def test_quote_of_the_day():
    day = date(2026, 10, 28)
    assert quote_of_the_day(day) == quote_of_the_day(day)
    assert quote_of_the_day(day)[1] != quote_of_the_day(day + timedelta(days=1))[1]
    assert all(len(quote) <= 140 and author for quote, author in QUOTES)
    assert len({quote for quote, _ in QUOTES}) == len(QUOTES)  # no repeats in the list


def test_the_quote_shows_on_today_and_the_login_page(owner_client, app, owner_id, client):
    add_habit(app, owner_id, "Walk")
    _, _, author = quote_of_the_day(today())
    page = owner_client.get("/").get_data(as_text=True)
    assert 'id="quotes-data"' in page and "data-next-quote" in page and author in page
    login = app.test_client().get("/login").get_data(as_text=True)
    assert "welcome-quote" in login


# ---------- Install on a phone ----------

def test_service_worker_and_manifest(client):
    response = client.get("/sw.js")
    assert response.status_code == 200 and "javascript" in response.content_type
    assert response.headers["Cache-Control"] == "no-cache"
    manifest = client.get("/static/site.webmanifest")
    assert manifest.content_type.startswith("application/manifest+json")
    for icon in manifest.get_json()["icons"]:
        assert client.get(f"/static/{icon['src']}").status_code == 200
    for name in ("icon-32.png", "apple-touch-icon.png"):
        assert client.get(f"/static/icons/{name}").status_code == 200
    assert client.get("/static/offline.html").status_code == 200
    csp = client.get("/login").headers["Content-Security-Policy"]
    assert "worker-src 'self'" in csp and "manifest-src 'self'" in csp


# ---------- The database upgrade ----------

def test_upgrade_an_old_database(tmp_path):
    """A database from before migration 1 (no habits.avoid) gets the column and keeps its data."""
    from gawi import create_app
    path = tmp_path / "old.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript((FIXTURES / "schema_v0.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO users (username, password_hash) VALUES ('juan', 'x')")
    connection.execute("""INSERT INTO habits (user_id, name, icon, color, kind, schedule, start_date, created_at)
                          VALUES (1, 'Walk', '🚶', 'green', 'check', 'daily', '2026-10-01', '2026-10-01')""")
    connection.commit()
    connection.close()

    app = create_app({"TESTING": True, "SECRET_KEY": "t", "DATABASE": str(path), "DATABASE_URL": None})
    with app.app_context():
        assert db.upgrade_db() == (0, len(db.MIGRATIONS))
        assert db.query_one("SELECT name, avoid FROM habits") == {"name": "Walk", "avoid": 0}
        assert db.upgrade_db() == (len(db.MIGRATIONS), len(db.MIGRATIONS))  # safe to run again


def test_upgrade_makes_the_tables_in_an_empty_database(tmp_path):
    """A brand-new database (like a new Neon one): upgrade-db makes everything, so the first deploy just works."""
    from gawi import create_app
    app = create_app({"TESTING": True, "SECRET_KEY": "t", "DATABASE": str(tmp_path / "new.sqlite"), "DATABASE_URL": None})
    result = app.test_cli_runner().invoke(args=["upgrade-db"])
    assert "made the tables" in result.output
    with app.app_context():
        assert db.has_tables() and db.schema_version() == len(db.MIGRATIONS)
        assert db.query("SELECT * FROM habits") == []
    # Run again: nothing to do, nothing lost.
    assert "up to date" in app.test_cli_runner().invoke(args=["upgrade-db"]).output


def test_render_runs_upgrade_db_before_the_app():
    text = (Path(__file__).parent.parent / "render.yaml").read_text(encoding="utf-8")
    assert "flask --app gawi upgrade-db && gunicorn" in text and "healthCheckPath: /healthz" in text
    assert "init-db" not in text  # init-db deletes everything; never on the live site


# ---------- The demo ----------

def test_the_demo_has_history_and_a_badge(app):
    with app.app_context():
        demo = auth.demo_user(auth.now())
        rows = db.query_one(
            "SELECT COUNT(*) AS n FROM checkins c JOIN habits h ON h.id = c.habit_id WHERE h.user_id = ?",
            (demo["id"],),
        )["n"]
        assert rows > 300
        pray = db.query_one("SELECT * FROM habits WHERE user_id = ? AND name = 'Pray'", (demo["id"],))
    history = seed.demo_history(auth.now().date())["Pray"]
    done = {day for day, (value, _) in history.items() if value}
    day = auth.now().date()
    assert streaks.current_streak(pray, done, set(), day) == seed.PRAY_STREAK
    assert streaks.earned(pray, seed.PRAY_STREAK) == [7, 30]


def test_the_demo_is_the_same_all_day():
    day = date(2026, 10, 28)
    assert seed.demo_history(day) == seed.demo_history(day)
