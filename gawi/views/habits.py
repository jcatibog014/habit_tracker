"""The Habits tab: the list, one habit's page, add, edit, archive, delete and reorder (by dragging)."""
from datetime import timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import db, grids, queries, streaks
from ..auth import login_required
from ..daily import day_sets
from ..dates import add_months
from ..validation import (
    COLOR_LABELS, COLORS, ICONS, KINDS, SCHEDULES, habit_form_values, validate_habit,
)
from . import owned_habit, user_today

bp = Blueprint("habits", __name__, url_prefix="/habits")

# Ideas on the empty list, to make the first habit one tap away:
# name -> (icon, colour, kind, target, unit).
SUGGESTIONS = {
    "Drink water": ("💧", "blue", "count", 8, "glasses"),
    "Walk": ("🚶", "green", "check", 1, ""),
    "Read": ("📚", "violet", "count", 10, "pages"),
    "Pray": ("🙏", "gold", "check", 1, ""),
    "Sleep by 10 PM": ("😴", "teal", "check", 1, ""),
    "Stretch": ("🧘", "pink", "check", 1, ""),
    "No soda": ("🥤", "red", "avoid", 1, ""),
}


def active_habits():
    return db.query(
        "SELECT * FROM habits WHERE user_id = ? AND archived_at IS NULL ORDER BY position, id",
        (g.user["id"],),
    )


def taken_names(except_id=None):
    """The lower-cased names of the user's other habits."""
    rows = db.query("SELECT id, name FROM habits WHERE user_id = ?", (g.user["id"],))
    return {row["name"].lower() for row in rows if row["id"] != except_id}


def read_form():
    """The form as a dict, with the ticked weekday boxes as a list."""
    return {**request.form.to_dict(), "weekdays": request.form.getlist("weekdays")}


def form_page(values, errors, habit=None):
    return render_template(
        "habit_form.html", values=values, errors=errors, habit=habit,
        icons=ICONS, colors=COLORS, color_labels=COLOR_LABELS, kinds=KINDS, schedules=SCHEDULES,
    ), 400 if errors else 200


@bp.get("")
@login_required
def index():
    archived = db.query(
        "SELECT * FROM habits WHERE user_id = ? AND archived_at IS NOT NULL ORDER BY archived_at DESC, name",
        (g.user["id"],),
    )
    return render_template(
        "habits.html", habits=active_habits(), archived=archived, suggestions=SUGGESTIONS,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    today = user_today()
    if request.method == "POST":
        data, errors = validate_habit(read_form(), taken_names(), today)
        if errors:
            return form_page(read_form(), errors)
        position = db.query_one(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next FROM habits WHERE user_id = ?",
            (g.user["id"],),
        )["next"]
        db.execute(
            """INSERT INTO habits (user_id, name, icon, color, kind, target, unit, schedule,
                                   weekdays, per_week, start_date, avoid, position, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (g.user["id"], data["name"], data["icon"], data["color"], data["kind"], data["target"],
             data["unit"], data["schedule"], data["weekdays"], data["per_week"], data["start_date"],
             data["avoid"], position, today.isoformat()),
        )
        db.commit()
        flash(f"{data['icon']} {data['name']} is on your list. Small steps, every day! 🌱")
        return redirect(url_for("habits.index"))

    # A new form: a friendly default, or one of the suggestions filled in.
    used_colors = {habit["color"] for habit in active_habits()}
    values = {
        "icon": ICONS[0],
        "color": next((c for c in COLORS if c not in used_colors), COLORS[0]),
        "kind": "check", "schedule": "daily", "weekdays": [], "per_week": 3,
        "start_date": today.isoformat(),
    }
    name = request.args.get("suggestion", "")
    if name in SUGGESTIONS:
        icon, color, kind, target, unit = SUGGESTIONS[name]
        values.update(name=name, icon=icon, color=color, kind=kind, unit=unit,
                      target=target if kind == "count" else "")
    return form_page(values, {})


@bp.route("/<int:habit_id>/edit", methods=["GET", "POST"])
@login_required
def edit(habit_id):
    habit = owned_habit(habit_id)
    if request.method == "POST":
        data, errors = validate_habit(read_form(), taken_names(except_id=habit_id), user_today())
        if errors:
            return form_page(read_form(), errors, habit)
        db.execute(
            """UPDATE habits SET name = ?, icon = ?, color = ?, kind = ?, target = ?, unit = ?,
                                 schedule = ?, weekdays = ?, per_week = ?, start_date = ?, avoid = ?
               WHERE id = ? AND user_id = ?""",
            (data["name"], data["icon"], data["color"], data["kind"], data["target"], data["unit"],
             data["schedule"], data["weekdays"], data["per_week"], data["start_date"], data["avoid"],
             habit_id, g.user["id"]),
        )
        db.commit()
        flash(f"Saved {data['icon']} {data['name']}.")
        return redirect(url_for("habits.detail", habit_id=habit_id))
    return form_page(habit_form_values(habit), {}, habit)


@bp.get("/<int:habit_id>")
@login_required
def detail(habit_id):
    """One habit's page: streaks, badges, the year heatmap and a month calendar."""
    habit = owned_habit(habit_id)
    today = user_today()
    start = streaks.start_of(habit)
    days = queries.history(g.user["id"], min(start, today), today, habit_id).get(habit_id, {})
    sets = day_sets(habit, days, today)
    done, rest, _ = sets

    current = streaks.current_streak(habit, done, rest, today)
    longest = streaks.longest_streak(habit, done, rest, today)
    upcoming = streaks.next_milestone(habit, current)
    month = grids.parse_month(request.args.get("month"), today)
    year_columns, year_months = grids.year_grid(habit, sets, days, today)
    return render_template(
        "habit.html",
        habit=habit,
        unit=streaks.unit(habit),
        current=current,
        longest=longest,
        score=streaks.completion(habit, done, rest, today - timedelta(days=29), today),
        total=len(done),
        milestones=streaks.MILESTONES[streaks.unit(habit)],
        earned=streaks.earned(habit, longest),
        upcoming=upcoming,
        to_go=upcoming - current if upcoming else None,
        month=month,
        month_weeks=grids.month_grid(habit, sets, days, month, today),
        previous_month=add_months(month, -1),
        next_month=add_months(month, 1) if month < today.replace(day=1) else None,
        year_columns=year_columns,
        year_months=year_months,
        monthly=grids.monthly_totals(habit, done, today),
        today=today,
        started=today >= start,
    )


@bp.post("/<int:habit_id>/archive")
@login_required
def archive(habit_id):
    """Archive a habit (hide it, keep its history), or bring an archived one back."""
    habit = owned_habit(habit_id)
    if habit["archived_at"]:
        # Back at the end of the list.
        position = db.query_one(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next FROM habits WHERE user_id = ?",
            (g.user["id"],),
        )["next"]
        db.execute("UPDATE habits SET archived_at = NULL, position = ? WHERE id = ?", (position, habit_id))
        flash(f"Welcome back, {habit['icon']} {habit['name']}! 💪")
    else:
        db.execute("UPDATE habits SET archived_at = ? WHERE id = ?", (user_today().isoformat(), habit_id))
        flash(f"Archived {habit['icon']} {habit['name']}. Its history is kept.")
    db.commit()
    return redirect(url_for("habits.index"))


@bp.post("/<int:habit_id>/delete")
@login_required
def delete(habit_id):
    habit = owned_habit(habit_id)
    # ON DELETE CASCADE removes its check-ins too.
    db.execute("DELETE FROM habits WHERE id = ? AND user_id = ?", (habit_id, g.user["id"]))
    db.commit()
    flash(f"Deleted {habit['icon']} {habit['name']} and its history.")
    return redirect(url_for("habits.index"))


@bp.post("/reorder")
@login_required
def reorder():
    """Save a new order after dragging: order="3,1,2" (habit ids, top first).

    It must name exactly the user's active habits, so nobody can move
    someone else's habit, or lose one by leaving it out.
    """
    try:
        ids = [int(part) for part in request.form.get("order", "").split(",")]
    except ValueError:
        abort(400, "That order is not a list of habits.")
    if sorted(ids) != sorted(habit["id"] for habit in active_habits()):
        abort(400, "That order doesn't match your habits. Reload the page and try again.")
    # Number them 0, 1, 2... so there are never two at the same place.
    db.execute_many(
        "UPDATE habits SET position = ? WHERE id = ? AND user_id = ?",
        [(position, habit_id, g.user["id"]) for position, habit_id in enumerate(ids)],
    )
    db.commit()
    return {"ok": True}
