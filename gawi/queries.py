"""The SQL that reads check-ins. Every query starts from the user's habits
(JOIN habits ... WHERE h.user_id = ?), because check-ins have no user_id."""
from . import db


def day_values(user_id, day):
    """{habit_id: value} for one day. Habits with no row there were not done."""
    rows = db.query(
        """SELECT c.habit_id, c.value
           FROM checkins c JOIN habits h ON h.id = c.habit_id
           WHERE h.user_id = ? AND c.day = ? AND c.skipped = 0""",
        (user_id, day.isoformat()),
    )
    return {row["habit_id"]: row["value"] for row in rows}


def done_days_between(user_id, first, last):
    """{habit_id: how many days it was done} from `first` to `last` (both included).

    "Done" means the day's value reached the habit's target, so the
    comparison needs the habit's row: that's what the JOIN is for.
    """
    rows = db.query(
        """SELECT c.habit_id, COUNT(*) AS days
           FROM checkins c JOIN habits h ON h.id = c.habit_id
           WHERE h.user_id = ? AND c.day BETWEEN ? AND ?
             AND c.skipped = 0 AND c.value >= h.target
           GROUP BY c.habit_id""",
        (user_id, first.isoformat(), last.isoformat()),
    )
    return {row["habit_id"]: row["days"] for row in rows}


def set_value(habit_id, day, value):
    """Save a habit's value for a day. 0 deletes the row: no row means "not done"."""
    if value <= 0:
        db.execute("DELETE FROM checkins WHERE habit_id = ? AND day = ?", (habit_id, day.isoformat()))
        return
    # An "upsert": add the row, or if this habit already has one for this day, change its value.
    db.execute(
        """INSERT INTO checkins (habit_id, day, value) VALUES (?, ?, ?)
           ON CONFLICT (habit_id, day) DO UPDATE SET value = excluded.value, skipped = 0""",
        (habit_id, day.isoformat(), value),
    )
