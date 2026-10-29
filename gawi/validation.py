"""Checking what people type into forms. No Flask here, so it's easy to test.

Each validate_*() takes the form as a plain dict and returns (data, errors):
`data` holds clean values ready for the database, and `errors` maps a
field name to a message. When `errors` is empty, `data` is safe to save.
"""
from datetime import date, timedelta

from .dates import parse_day

NAME_MAX_LENGTH = 40
UNIT_MAX_LENGTH = 20
TARGET_MAX = 1000
START_MIN = date(2000, 1, 1)
START_MAX_AHEAD = timedelta(days=365)  # you can plan a habit up to a year ahead

# The emoji a habit can have. A fixed list keeps the picker tidy.
# 36 of them, so the grid has full rows: 9 across on a computer, 6 on a phone.
ICONS = [
    "✅", "💧", "🚶", "🏃", "🧘", "💪", "🚴", "🏊", "⚽",
    "📚", "✍️", "🎸", "🎨", "🧠", "💻", "🎵", "🧹", "🛏️",
    "🙏", "😴", "🥗", "🍎", "☕", "🚭", "💊", "🦷", "🥤",
    "🌱", "☀️", "🌙", "📵", "💰", "❤️", "🐶", "📞", "🎯",
]

# Habit colours: bright, and all at least 3:1 against the card in both themes
# (CSS has the shades, as --habit-<name>). The form shows them in this order.
COLORS = ["orange", "red", "gold", "green", "teal", "blue", "violet", "pink"]
COLOR_LABELS = {
    "orange": "Sunrise orange", "red": "Coral red", "gold": "Gold", "green": "Leaf green",
    "teal": "Teal", "blue": "Sky blue", "violet": "Violet", "pink": "Pink",
}

# "avoid" is a yes/no habit with habits.avoid = 1 (a check-in means "I slipped").
KINDS = {"check": "Yes or no", "count": "Count", "avoid": "Avoid it"}
SCHEDULES = {"daily": "Every day", "weekdays": "On some days", "weekly": "Some times a week"}


def _whole_number(text, low, high):
    """ "8" -> 8 if low <= 8 <= high, else None."""
    try:
        number = int(str(text).strip())
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None


def validate_habit(form, taken_names, today):
    """Check the habit form.

    form: the fields as a dict; "weekdays" is a list of the ticked boxes ("1".."7").
    taken_names: lower-cased names of the user's other habits (two habits can't share a name).
    today: the user's today, for the start date.
    """
    errors = {}
    data = {}

    name = " ".join((form.get("name") or "").split())  # trim, and no double spaces
    if not name:
        errors["name"] = "Give your habit a name."
    elif len(name) > NAME_MAX_LENGTH:
        errors["name"] = f"Use at most {NAME_MAX_LENGTH} characters."
    elif name.lower() in taken_names:
        errors["name"] = "You already have a habit with this name."
    data["name"] = name

    icon = form.get("icon") or ""
    if icon not in ICONS:
        errors["icon"] = "Choose an icon."
    data["icon"] = icon

    color = form.get("color") or ""
    if color not in COLORS:
        errors["color"] = "Choose a colour."
    data["color"] = color

    kind = form.get("kind") or ""
    if kind not in KINDS:
        errors["kind"] = "Choose how you track it."
    # A habit to avoid is stored as a yes/no habit with the avoid flag.
    data["avoid"] = 1 if kind == "avoid" else 0
    data["kind"] = "check" if kind == "avoid" else kind
    data["target"], data["unit"] = 1, ""
    if kind == "count":
        target = _whole_number(form.get("target"), 2, TARGET_MAX)
        if target is None:
            # A count of 1 is just yes/no, so a count goal starts at 2.
            errors["target"] = f"Use a whole number from 2 to {TARGET_MAX}."
        unit = " ".join((form.get("unit") or "").split())
        if len(unit) > UNIT_MAX_LENGTH:
            errors["unit"] = f"Use at most {UNIT_MAX_LENGTH} characters."
        data["target"], data["unit"] = target, unit

    schedule = form.get("schedule") or ""
    if schedule not in SCHEDULES:
        errors["schedule"] = "Choose when to do it."
    data["schedule"] = schedule
    data["weekdays"], data["per_week"] = "", None
    if schedule == "weekdays":
        days = sorted({day for day in (_whole_number(d, 1, 7) for d in form.get("weekdays") or []) if day})
        if not days:
            errors["weekdays"] = "Tick at least one day."
        elif len(days) == 7:
            data["schedule"] = "daily"  # all seven days is just every day
        else:
            data["weekdays"] = ",".join(str(day) for day in days)
    elif schedule == "weekly":
        per_week = _whole_number(form.get("per_week"), 1, 6)
        if per_week is None:
            errors["per_week"] = "Use a number from 1 to 6. (7 is every day.)"
        data["per_week"] = per_week

    start = parse_day(form.get("start_date"))
    if start is None:
        errors["start_date"] = "Choose a start date."
    elif start < START_MIN:
        errors["start_date"] = "Choose a date in the year 2000 or later."
    elif start > today + START_MAX_AHEAD:
        errors["start_date"] = "Choose a date less than a year from now."
    data["start_date"] = start.isoformat() if start else ""

    return data, errors


def habit_form_values(habit):
    """A saved habit as the values its edit form shows (the opposite of validate_habit)."""
    return {
        **habit,
        "kind": "avoid" if habit.get("avoid") else habit["kind"],
        "weekdays": (habit["weekdays"] or "").split(","),
        "target": habit["target"] if habit["kind"] == "count" else "",
        "per_week": habit["per_week"] or "",
    }
