"""One day's list of habits, in plain Python (no Flask, no SQL).

The Today page asks: which habits are for today, which are done, and how
far along am I? build_day() answers from the habits and two small lookups
the caller got from the database (see queries.py).
"""
from .schedule import describe, goal, is_due


def habit_card(habit, value, week_done):
    """One habit on a day: its value, whether it's done, and the short line under its name."""
    done = value >= habit["target"]
    if habit["kind"] == "count":
        line = f"{value} / {goal(habit)}"
    else:
        line = describe(habit)
    if habit["schedule"] == "weekly":
        line = f"{min(week_done, habit['per_week'])} of {habit['per_week']} this week"
        if habit["kind"] == "count":
            line = f"{value} / {goal(habit)} · " + line
    return {
        "habit": habit,
        "value": value,
        "done": done,
        "line": line,
        # A count goal shows how full its ring is.
        "percent": min(100, round(100 * value / habit["target"])),
    }


def build_day(habits, values, week_done, day):
    """Split the user's active habits into the ones for `day` and the rest.

    habits: active habits, in the user's order.
    values: {habit_id: that day's value}.
    week_done: {habit_id: days done this week so far, `day` included}.

    A weekly habit ("3 times a week") is for today until the week's goal was
    reached on earlier days. After that it moves to the rest, still tickable.
    Returns {"due": [cards], "rest": [cards], "done": n, "total": n}.
    """
    due, rest = [], []
    for habit in habits:
        value = values.get(habit["id"], 0)
        card = habit_card(habit, value, week_done.get(habit["id"], 0))
        if not is_due(habit, day):
            rest.append(card)
        elif habit["schedule"] == "weekly":
            done_before_today = week_done.get(habit["id"], 0) - (1 if card["done"] else 0)
            card["week_reached"] = done_before_today >= habit["per_week"]
            (rest if card["week_reached"] else due).append(card)
        else:
            due.append(card)
    return {
        "due": due,
        "rest": rest,
        "done": sum(1 for card in due if card["done"]),
        "total": len(due),
    }
