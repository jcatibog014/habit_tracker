"""The Today page (home), ticking habits off, and the health check."""
from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from .. import db, queries
from ..auth import login_required
from ..daily import build_day
from ..dates import long_date, now
from ..messages import greeting, progress_message
from ..schedule import week_start
from ..validation import TARGET_MAX
from . import owned_habit, user_today
from .habits import SUGGESTIONS, active_habits

bp = Blueprint("main", __name__)


@bp.get("/healthz")
def health():
    """Render calls this to check the site is up. No login and no database, so it's quick."""
    return {"status": "ok"}


def load_day(day):
    """Today's habits, split into "for today" and the rest (see daily.build_day)."""
    user_id = g.user["id"]
    return build_day(
        active_habits(),
        queries.day_values(user_id, day),
        queries.done_days_between(user_id, week_start(day), day),
        day,
    )


def summary(day_data):
    done, total = day_data["done"], day_data["total"]
    return {
        "done": done,
        "total": total,
        "percent": round(100 * done / total) if total else 100,
        "message": progress_message(done, total),
    }


@bp.get("/")
@login_required
def home():
    today = user_today()
    words, emoji = greeting(now(g.user["timezone"]).hour)
    day_data = load_day(today)
    return render_template(
        "today.html",
        greeting=words, greeting_emoji=emoji,
        date_label=long_date(today),
        day=day_data,
        summary=summary(day_data),
        suggestions=SUGGESTIONS,
    )


@bp.post("/checkin/<int:habit_id>")
@login_required
def checkin(habit_id):
    """Tick a habit for today (action=toggle), or count one more or one less (plus/minus).

    The page's JavaScript sends this with fetch() and gets JSON back, so the
    page doesn't reload. Without JavaScript the form posts and we go back home.
    """
    habit = owned_habit(habit_id)
    today = user_today()
    if habit["archived_at"]:
        abort(404)
    # A habit on its day off can still be ticked (an extra is nice!), but not before it starts.
    if today.isoformat() < habit["start_date"]:
        abort(400, "This habit hasn't started yet.")

    value = queries.day_values(g.user["id"], today).get(habit_id, 0)
    action = request.form.get("action")
    if action == "toggle":
        value = 0 if value >= habit["target"] else habit["target"]
    elif action == "plus":
        value = min(value + 1, TARGET_MAX)
    elif action == "minus":
        value = max(value - 1, 0)
    else:
        abort(400, "Unknown action.")
    queries.set_value(habit_id, today, value)
    db.commit()

    if request.accept_mimetypes.best != "application/json":
        return redirect(url_for("main.home", _anchor=f"habit-{habit_id}"))
    day_data = load_day(today)
    card = next(card for card in day_data["due"] + day_data["rest"] if card["habit"]["id"] == habit_id)
    return {
        "value": card["value"],
        "done": card["done"],
        "line": card["line"],
        "percent": card["percent"],
        "summary": summary(day_data),
    }
