"""The SQL that reads and writes check-ins. Every query starts from the user's
habits (JOIN habits ... WHERE h.user_id = ?), because check-ins have no user_id."""
from datetime import date

from . import db


def history(user_id, first, last, habit_id=None):
    """{habit_id: {day: (value, skipped)}} for the user's check-ins from `first` to `last`.

    One query for all habits (or just one). Streaks need the whole run of
    days, and one query is much faster than one per habit, above all over
    the network to Neon.
    """
    sql = """SELECT c.habit_id, c.day, c.value, c.skipped
             FROM checkins c JOIN habits h ON h.id = c.habit_id
             WHERE h.user_id = ? AND c.day BETWEEN ? AND ?"""
    params = [user_id, first.isoformat(), last.isoformat()]
    if habit_id is not None:
        sql += " AND c.habit_id = ?"
        params.append(habit_id)
    result = {}
    for row in db.query(sql, params):
        result.setdefault(row["habit_id"], {})[date.fromisoformat(row["day"])] = (row["value"], row["skipped"])
    return result


def day_entry(habit_id, day):
    """(value, skipped) for one habit on one day; (0, 0) when there's no row."""
    row = db.query_one(
        "SELECT value, skipped FROM checkins WHERE habit_id = ? AND day = ?", (habit_id, day.isoformat())
    )
    return (row["value"], row["skipped"]) if row else (0, 0)


def set_value(habit_id, day, value):
    """Save a habit's value for a day (and end a rest day). 0 deletes the row: no row means "not done"."""
    if value <= 0:
        db.execute("DELETE FROM checkins WHERE habit_id = ? AND day = ?", (habit_id, day.isoformat()))
        return
    # An "upsert": add the row, or if this habit already has one for this day, change its value.
    db.execute(
        """INSERT INTO checkins (habit_id, day, value) VALUES (?, ?, ?)
           ON CONFLICT (habit_id, day) DO UPDATE SET value = excluded.value, skipped = 0""",
        (habit_id, day.isoformat(), value),
    )


def set_rest(habit_id, day, on):
    """Make a day a rest day (value 0, skipped 1), or take the rest day away."""
    if not on:
        db.execute("DELETE FROM checkins WHERE habit_id = ? AND day = ?", (habit_id, day.isoformat()))
        return
    db.execute(
        """INSERT INTO checkins (habit_id, day, value, skipped) VALUES (?, ?, 0, 1)
           ON CONFLICT (habit_id, day) DO UPDATE SET value = 0, skipped = 1""",
        (habit_id, day.isoformat()),
    )
