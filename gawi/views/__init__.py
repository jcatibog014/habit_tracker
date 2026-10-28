"""The pages, one blueprint per part of the app, plus helpers they share."""
from flask import abort, g

from .. import db
from ..dates import today


def user_today():
    """Today in the logged-in user's time zone."""
    return today(g.user["timezone"])


def owned_habit(habit_id):
    """The habit with this id, if it belongs to the logged-in user. Otherwise 404.

    We answer "not found" (and not "forbidden") for other people's habits, so
    nobody can find out which ids exist.
    """
    habit = db.query_one(
        "SELECT * FROM habits WHERE id = ? AND user_id = ?", (habit_id, g.user["id"])
    )
    if habit is None:
        abort(404)
    return habit
