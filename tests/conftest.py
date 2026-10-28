import os

import pytest

from gawi import auth, create_app, db

# Tests use a fresh SQLite file per test. To check the SQL on PostgreSQL too,
# set TEST_DATABASE_URL to an empty Neon branch (its tables are dropped and
# made again for every test, so never point it at the live database).
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

CSRF = "test-csrf-token"
OWNER = "juan"
OWNER_PASSWORD = "correct horse"


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "DATABASE": str(tmp_path / "test.sqlite"),
        "DATABASE_URL": TEST_DATABASE_URL,
    })
    with app.app_context():
        db.init_db()
        auth.create_user(OWNER, OWNER_PASSWORD)
        db.commit()
    return app


@pytest.fixture
def client(app):
    client = app.test_client()
    # Every POST needs the session's CSRF token. Put a known one in the session.
    with client.session_transaction() as session:
        session["csrf"] = CSRF
    return client


def post(client, url, data=None, **kwargs):
    """POST a form with the right CSRF token, like a real page would."""
    # Logging in or out starts a new session (and a new token), so set it every time.
    with client.session_transaction() as session:
        session["csrf"] = CSRF
    return client.post(url, data={"csrf_token": CSRF, **(data or {})}, **kwargs)


def log_in_as(client, user_id):
    """Skip the login form: put the user straight into the session."""
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["csrf"] = CSRF


def user_id(app, username):
    with app.app_context():
        return db.query_one("SELECT id FROM users WHERE username = ?", (username,))["id"]


def make_user(app, username):
    with app.app_context():
        new_id = auth.create_user(username, "another password")
        db.commit()
        return new_id


def add_habit(app, user_id, name="Drink water", **fields):
    """Put one habit straight into the database. Returns its id."""
    habit = {
        "icon": "💧", "color": "blue", "kind": "check", "target": 1, "unit": "",
        "schedule": "daily", "weekdays": "", "per_week": None,
        "start_date": "2026-10-01", "archived_at": None, "position": 0,
        "created_at": "2026-10-01", **fields,
    }
    with app.app_context():
        habit_id = db.insert(
            """INSERT INTO habits (user_id, name, icon, color, kind, target, unit, schedule, weekdays,
                                   per_week, start_date, archived_at, position, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            (user_id, name, habit["icon"], habit["color"], habit["kind"], habit["target"], habit["unit"],
             habit["schedule"], habit["weekdays"], habit["per_week"], habit["start_date"],
             habit["archived_at"], habit["position"], habit["created_at"]),
        )
        db.commit()
        return habit_id


def get_habit(app, habit_id):
    with app.app_context():
        return db.query_one("SELECT * FROM habits WHERE id = ?", (habit_id,))


# A filled-in "new habit" form that passes validation.
HABIT_FORM = {
    "name": "Read", "icon": "📚", "color": "violet", "kind": "check",
    "schedule": "daily", "start_date": "2026-10-01",
}


@pytest.fixture
def owner_id(app):
    return user_id(app, OWNER)


@pytest.fixture
def other_id(app):
    """A second user, to check that nobody sees another user's habits."""
    return make_user(app, "pedro")


@pytest.fixture
def owner_client(client, owner_id):
    log_in_as(client, owner_id)
    return client
