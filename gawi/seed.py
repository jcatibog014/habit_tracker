"""Sample data for the demo account.

The demo is shared by every visitor, so reset_demo() throws its habits
away and makes them again. Start dates are counted back from today, so
the demo always looks like someone who started about three months ago.
"""
from datetime import timedelta

from . import db
from .dates import DEFAULT_TIMEZONE

DEMO_START_DAYS_AGO = 90

# (name, icon, color, kind, target, unit, schedule, weekdays, per_week)
DEMO_HABITS = [
    ("Drink water", "💧", "blue", "count", 8, "glasses", "daily", "", None),
    ("Morning walk", "🚶", "green", "check", 1, "", "daily", "", None),
    ("Read", "📚", "violet", "count", 20, "pages", "daily", "", None),
    ("Pray", "🙏", "gold", "check", 1, "", "daily", "", None),
    ("Workout", "💪", "orange", "check", 1, "", "weekdays", "1,3,5", None),
    ("Call Lola", "📞", "pink", "check", 1, "", "weekly", "", 2),
]


def reset_demo(user_id, today):
    """Delete the demo's habits (their check-ins go too) and add the sample ones. The caller commits."""
    db.execute("DELETE FROM habits WHERE user_id = ?", (user_id,))
    db.execute("UPDATE users SET timezone = ? WHERE id = ?", (DEFAULT_TIMEZONE, user_id))
    start = (today - timedelta(days=DEMO_START_DAYS_AGO)).isoformat()
    db.execute_many(
        """INSERT INTO habits (user_id, name, icon, color, kind, target, unit, schedule,
                               weekdays, per_week, start_date, position, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(user_id, *habit, start, position, start) for position, habit in enumerate(DEMO_HABITS)],
    )
