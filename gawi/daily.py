"""One day's list of habits, in plain Python (no Flask, no SQL).

The Today page asks: which habits are for today, which are done, how long
is each streak, and how far along am I? build_day() answers from the
habits and their history (see queries.history).
"""
from datetime import timedelta

from . import streaks
from .messages import nudge
from .schedule import describe, goal, is_due, week_start


def day_sets(habit, days, today):
    """Turn one habit's rows {day: (value, skipped)} into (done, rest, slips) sets of days.

    For a normal habit, a day is done when its value reaches the target.
    For a habit to avoid, a row means "I slipped", so every day from the
    start until today *without* a slip (or a rest) is done.
    """
    rest = {day for day, (value, skipped) in days.items() if skipped}
    if not habit.get("avoid"):
        done = {day for day, (value, skipped) in days.items()
                if not skipped and value >= habit["target"]}
        return done, rest, set()

    slips = {day for day, (value, skipped) in days.items() if not skipped and value >= 1}
    done = set()
    day = streaks.start_of(habit)
    while day <= today:
        if day not in slips and day not in rest:
            done.add(day)
        day += timedelta(days=1)
    return done, rest, slips


def habit_card(habit, days, today):
    """One habit on `today`: its value, state, streak and the short line under its name."""
    done_days, rest, slips = day_sets(habit, days, today)
    value, skipped = days.get(today, (0, 0))
    rested = bool(skipped)
    slipped = today in slips
    if habit.get("avoid"):
        done = not slipped and not rested
    else:
        done = not rested and value >= habit["target"]

    streak = streaks.current_streak(habit, done_days, rest, today)
    longest = streaks.longest_streak(habit, done_days, rest, today)
    unit = streaks.unit(habit)

    if rested:
        line = "Rest day"
    elif habit.get("avoid"):
        line = "Slipped today. Tomorrow is a new day." if slipped else "Clean today"
    elif habit["kind"] == "count":
        line = f"{value} / {goal(habit)}"
    else:
        line = describe(habit)

    # A count goal shows how full its ring is; the others are all or nothing.
    if done:
        percent = 100
    elif habit.get("avoid"):
        percent = 0
    else:
        percent = min(100, round(100 * value / habit["target"]))

    week_done = 0
    if habit["schedule"] == "weekly":
        monday = week_start(today)
        week_done = sum(1 for day in done_days if monday <= day <= today)
        if not rested:
            week_line = f"{min(week_done, habit['per_week'])} of {habit['per_week']} this week"
            line = f"{line} · {week_line}" if habit["kind"] == "count" else week_line

    return {
        "habit": habit,
        "value": value,
        "done": done,
        "rested": rested,
        "slipped": slipped,
        "line": line,
        "streak": streak,
        "longest": longest,
        "unit": unit,
        # After a slip, the line already says "Tomorrow is a new day": no push on top.
        "nudge": nudge(streak, longest, unit, done or rested or slipped),
        "week_done": week_done,
        "percent": percent,
    }


def build_day(habits, history, day):
    """Split the user's active habits into the ones for `day` and the rest.

    habits: active habits, in the user's order.
    history: {habit_id: {date: (value, skipped)}} from the start of the
        habits until `day` (streaks need the whole run).

    A weekly habit ("3 times a week") is for today until the week's goal was
    reached on earlier days. After that it moves to the rest, still tickable.
    A rest day isn't counted in the progress ring at all.
    Returns {"due": [cards], "rest": [cards], "done": n, "total": n}.
    """
    due, rest = [], []
    for habit in habits:
        card = habit_card(habit, history.get(habit["id"], {}), day)
        if not is_due(habit, day):
            rest.append(card)
        elif habit["schedule"] == "weekly":
            done_before_today = card["week_done"] - (1 if card["done"] else 0)
            card["week_reached"] = done_before_today >= habit["per_week"]
            (rest if card["week_reached"] else due).append(card)
        else:
            due.append(card)
    counted = [card for card in due if not card["rested"]]
    return {
        "due": due,
        "rest": rest,
        "done": sum(1 for card in counted if card["done"]),
        "total": len(counted),
    }


def done_by_week(habits, history, today):
    """{monday: how many habit-days were done that week}, for "best week ever"."""
    weeks = {}
    for habit in habits:
        done_days, _, _ = day_sets(habit, history.get(habit["id"], {}), today)
        for day in done_days:
            if habit.get("avoid"):
                continue  # a clean day isn't something you did; don't let it inflate the count
            monday = week_start(day)
            weeks[monday] = weeks.get(monday, 0) + 1
    return weeks
