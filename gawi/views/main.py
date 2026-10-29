"""The Today page (home), ticking habits off, and the health check."""
from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for,
)

from .. import db, queries, streaks
from ..auth import login_required, safe_next
from ..daily import build_day, done_by_week, habit_card
from ..dates import long_date, now, parse_day
from ..messages import QUOTES, greeting, milestone_message, progress_message, quote_of_the_day
from ..schedule import week_start
from ..validation import TARGET_MAX
from . import owned_habit, user_today
from .habits import SUGGESTIONS, active_habits

bp = Blueprint("main", __name__)


@bp.get("/healthz")
def health():
    """Render calls this to check the site is up. No login and no database, so it's quick."""
    return {"status": "ok"}


@bp.get("/sw.js")
def service_worker():
    """The service worker (it makes Gawi installable on a phone).

    It's served from the top of the site, not /static/, because a service
    worker only looks after the pages below the address it came from.
    """
    response = current_app.send_static_file("sw.js")
    response.headers["Cache-Control"] = "no-cache"  # always check for a new version
    return response


def history_for(habits, day):
    """All check-ins of these habits, from the first start date until `day`."""
    first = min([streaks.start_of(habit) for habit in habits] + [day])
    return queries.history(g.user["id"], first, day)


def load_day(day):
    """Today's habits, split into "for today" and the rest (see daily.build_day)."""
    habits = active_habits()
    history = history_for(habits, day)
    day_data = build_day(habits, history, day)
    day_data["best_week"] = streaks.is_best_week(done_by_week(habits, history, day), week_start(day))
    return day_data


def summary(day_data):
    done, total = day_data["done"], day_data["total"]
    return {
        "done": done,
        "total": total,
        "percent": round(100 * done / total) if total else 100,
        "message": progress_message(done, total, day_data.get("best_week", False)),
    }


@bp.get("/")
@login_required
def home():
    today = user_today()
    words, emoji = greeting(now(g.user["timezone"]).hour)
    day_data = load_day(today)
    index, quote, author = quote_of_the_day(today)
    return render_template(
        "today.html",
        greeting=words, greeting_emoji=emoji,
        date_label=long_date(today),
        day=day_data,
        summary=summary(day_data),
        suggestions=SUGGESTIONS,
        quote=quote, quote_author=author, quote_index=index,
        quotes=[{"quote": q, "author": a} for q, a in QUOTES],
    )


def card_for(habit, today):
    """The habit's card for today, with its streak (from its whole history)."""
    days = queries.history(g.user["id"], min(streaks.start_of(habit), today), today, habit["id"])
    return habit_card(habit, days.get(habit["id"], {}), today)


def apply_action(habit, day, action):
    """Change one day of one habit. The caller commits."""
    value, skipped = queries.day_entry(habit["id"], day)
    if skipped:
        value = 0  # a rest day has no value; ticking it ends the rest
    target = habit["target"]
    if action == "rest":
        queries.set_rest(habit["id"], day, not skipped)
    elif action == "toggle":
        # For a habit to avoid, this records (or takes back) a slip.
        queries.set_value(habit["id"], day, 0 if value >= target else target)
    elif action == "plus":
        queries.set_value(habit["id"], day, min(value + 1, TARGET_MAX))
    elif action == "minus":
        queries.set_value(habit["id"], day, max(value - 1, 0))
    elif action == "cycle":
        # The calendar on a habit's page: not done -> done -> rest -> not done.
        # (For a habit to avoid: clean -> slipped -> rest -> clean.)
        if skipped:
            queries.set_rest(habit["id"], day, False)
        elif value >= target:
            queries.set_rest(habit["id"], day, True)
        else:
            queries.set_value(habit["id"], day, target)
    else:
        abort(400, "Unknown action.")


@bp.post("/checkin/<int:habit_id>")
@login_required
def checkin(habit_id):
    """Change a habit's day: action = toggle, plus, minus, rest or cycle; day = today unless given.

    The Today page's JavaScript sends this with fetch() and gets JSON back,
    so the page doesn't reload. Plain forms (the calendar, or no JavaScript)
    go back to the page they came from.
    """
    habit = owned_habit(habit_id)
    today = user_today()
    if habit["archived_at"]:
        abort(404)
    day = parse_day(request.form.get("day")) or today
    if day > today:
        abort(400, "That day hasn't come yet.")
    # A habit on its day off can still be ticked (an extra is nice!), but not before it starts.
    if day < streaks.start_of(habit):
        abort(400, "This habit hadn't started yet on that day.")

    before = card_for(habit, today)
    apply_action(habit, day, request.form.get("action"))
    db.commit()
    after = card_for(habit, today)

    reached = streaks.just_reached(habit, before["streak"], after["streak"])
    milestone = None
    if reached:
        milestone = {"count": reached, "unit": after["unit"],
                     "message": milestone_message(habit["name"], reached, after["unit"])}

    if request.accept_mimetypes.best != "application/json":
        if milestone:
            flash(milestone["message"])
        back = url_for("main.home", _anchor=f"habit-{habit_id}")
        return redirect(safe_next(request.form.get("next"), back))
    return {
        "value": after["value"],
        "done": after["done"],
        "rested": after["rested"],
        "slipped": after["slipped"],
        "line": after["line"],
        "nudge": after["nudge"],
        "percent": after["percent"],
        "streak": after["streak"],
        "unit": after["unit"],
        "summary": summary(load_day(today)),
        "milestone": milestone,
    }
