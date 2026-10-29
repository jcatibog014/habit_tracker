"""Sample data for the demo account.

The demo is shared by every visitor, so reset_demo() throws its habits
away and makes them again, with about three months of history. Every
date is counted back from today, so the demo always looks like someone
who started three months ago and is doing well (but not perfectly).

The history comes from random.Random(today): the same day always gives
the same demo, which keeps tests and screenshots steady.
"""
import random
from datetime import timedelta

from . import db
from .dates import DEFAULT_TIMEZONE

DEMO_START_DAYS_AGO = 90
PRAY_STREAK = 34  # days in a row, up to yesterday: the 30-day badge is earned

# (name, icon, color, kind, target, unit, schedule, weekdays, per_week, avoid)
DEMO_HABITS = [
    ("Drink water", "💧", "blue", "count", 8, "glasses", "daily", "", None, 0),
    ("Morning walk", "🚶", "green", "check", 1, "", "daily", "", None, 0),
    ("Read", "📚", "violet", "count", 20, "pages", "daily", "", None, 0),
    ("Pray", "🙏", "gold", "check", 1, "", "daily", "", None, 0),
    ("Workout", "💪", "orange", "check", 1, "", "weekdays", "1,3,5", None, 0),
    ("Call Lola", "📞", "pink", "check", 1, "", "weekly", "", 2, 0),
    ("No soda", "🥤", "red", "check", 1, "", "daily", "", None, 1),
]

SODA_SLIPS = [70, 41, 12]  # days ago
REST_DAYS = {"Morning walk": [20], "Workout": [9]}  # days ago (Workout's falls on whatever day it falls)


def demo_history(today):
    """{habit name: {day: (value, skipped)}} for the demo, up to today."""
    rng = random.Random(today.isoformat())
    start = today - timedelta(days=DEMO_START_DAYS_AGO)
    history = {name: {} for name, *_ in DEMO_HABITS}

    for back in range(DEMO_START_DAYS_AGO, 0, -1):  # every day before today
        day = today - timedelta(days=back)
        weekend = day.isoweekday() >= 6
        if rng.random() < 0.85:
            history["Drink water"][day] = (8, 0)
        else:
            history["Drink water"][day] = (rng.randint(3, 7), 0)
        if rng.random() < (0.6 if weekend else 0.85):
            history["Morning walk"][day] = (1, 0)
        roll = rng.random()
        if roll < 0.7:
            history["Read"][day] = (rng.randint(20, 32), 0)
        elif roll < 0.85:
            history["Read"][day] = (rng.randint(5, 15), 0)
        # Pray: an unbroken run lately, and a good (not perfect) record before it.
        if back <= PRAY_STREAK or (back != PRAY_STREAK + 1 and rng.random() < 0.85):
            history["Pray"][day] = (1, 0)
        if day.isoweekday() in (1, 3, 5) and rng.random() < 0.8:
            history["Workout"][day] = (1, 0)

    # Call Lola: two days most weeks, one day in some.
    monday = start - timedelta(days=start.weekday())
    while monday < today - timedelta(days=today.weekday()):
        days = [monday + timedelta(days=i) for i in range(7)]
        for day in rng.sample(days, 2 if rng.random() < 0.8 else 1):
            if start <= day < today:
                history["Call Lola"][day] = (1, 0)
        monday += timedelta(days=7)

    for back in SODA_SLIPS:
        history["No soda"][today - timedelta(days=back)] = (1, 0)
    for name, backs in REST_DAYS.items():
        for back in backs:
            history[name][today - timedelta(days=back)] = (0, 1)

    # Today is under way: some done, some not yet (so the nudges show).
    history["Drink water"][today] = (3, 0)
    history["Read"][today] = (10, 0)
    history["Morning walk"][today] = (1, 0)
    return history


def reset_demo(user_id, today):
    """Delete the demo's habits (their check-ins go too) and add the samples. The caller commits."""
    db.execute("DELETE FROM habits WHERE user_id = ?", (user_id,))
    db.execute("UPDATE users SET timezone = ? WHERE id = ?", (DEFAULT_TIMEZONE, user_id))
    start = (today - timedelta(days=DEMO_START_DAYS_AGO)).isoformat()
    ids = {}
    for position, habit in enumerate(DEMO_HABITS):
        ids[habit[0]] = db.insert(
            """INSERT INTO habits (user_id, name, icon, color, kind, target, unit, schedule,
                                   weekdays, per_week, avoid, start_date, position, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            (user_id, *habit, start, position, start),
        )
    rows = [
        (ids[name], day.isoformat(), value, skipped)
        for name, days in demo_history(today).items()
        for day, (value, skipped) in days.items()
    ]
    db.execute_many("INSERT INTO checkins (habit_id, day, value, skipped) VALUES (?, ?, ?, ?)", rows)
