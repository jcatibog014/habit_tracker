"""daily.build_day(), schedule.is_due() and the friendly messages, with fixed dates."""
from datetime import date, timedelta

from gawi.daily import build_day, day_sets
from gawi.messages import greeting, progress_message
from gawi.schedule import is_due, week_start

WEDNESDAY = date(2026, 10, 28)


def habit(habit_id, **fields):
    return {"id": habit_id, "name": f"H{habit_id}", "kind": "check", "target": 1, "unit": "",
            "schedule": "daily", "weekdays": "", "per_week": None, "start_date": "2026-10-01", **fields}


def test_week_starts_on_monday():
    assert week_start(WEDNESDAY) == date(2026, 10, 26)
    assert week_start(date(2026, 10, 26)) == date(2026, 10, 26)
    assert week_start(date(2026, 11, 1)) == date(2026, 10, 26)  # Sunday
    assert week_start(date(2027, 1, 1)) == date(2026, 12, 28)  # across a new year


def test_is_due():
    assert is_due(habit(1), WEDNESDAY)
    assert is_due(habit(1, schedule="weekdays", weekdays="1,3,5"), WEDNESDAY)
    assert not is_due(habit(1, schedule="weekdays", weekdays="2,4"), WEDNESDAY)
    assert is_due(habit(1, schedule="weekly", per_week=2), WEDNESDAY)
    assert not is_due(habit(1, start_date="2026-10-29"), WEDNESDAY)  # starts tomorrow
    assert is_due(habit(1, start_date="2026-10-28"), WEDNESDAY)  # starts today


MONDAY, TUESDAY = date(2026, 10, 26), date(2026, 10, 27)


def test_build_day_splits_and_counts():
    habits = [
        habit(1),
        habit(2, schedule="weekdays", weekdays="2,4"),  # not on Wednesdays
        habit(3, kind="count", target=8, unit="glasses"),
    ]
    history = {1: {WEDNESDAY: (1, 0)}, 3: {WEDNESDAY: (5, 0)}}
    day = build_day(habits, history, WEDNESDAY)
    assert [card["habit"]["id"] for card in day["due"]] == [1, 3]
    assert [card["habit"]["id"] for card in day["rest"]] == [2]
    assert (day["done"], day["total"]) == (1, 2)
    water = day["due"][1]
    assert (water["done"], water["line"], water["percent"]) == (False, "5 / 8 glasses", 62)


def test_a_count_over_the_goal_is_still_done_and_the_ring_stays_full():
    day = build_day([habit(1, kind="count", target=8)], {1: {WEDNESDAY: (12, 0)}}, WEDNESDAY)
    assert day["due"][0]["done"] and day["due"][0]["percent"] == 100


def test_a_weekly_habit_leaves_today_once_the_week_goal_was_reached_before():
    weekly = habit(1, schedule="weekly", per_week=2)
    # Done Mon and Tue, not today: the week is done, so it's not for today.
    day = build_day([weekly], {1: {MONDAY: (1, 0), TUESDAY: (1, 0)}}, WEDNESDAY)
    assert day["due"] == [] and day["rest"][0]["week_reached"]
    # Done Mon only: still for today.
    day = build_day([weekly], {1: {MONDAY: (1, 0)}}, WEDNESDAY)
    assert day["due"][0]["line"] == "1 of 2 this week"
    # Done Mon and today: today's tick reached the goal, so it stays (and is done).
    day = build_day([weekly], {1: {MONDAY: (1, 0), WEDNESDAY: (1, 0)}}, WEDNESDAY)
    assert day["due"][0]["done"] and (day["done"], day["total"]) == (1, 1)


def test_cards_carry_the_streak_and_a_nudge():
    # Done the 3 days before today, not yet today: the streak is 3 and worth protecting.
    history = {1: {WEDNESDAY - timedelta(days=n): (1, 0) for n in (1, 2, 3)}}
    card = build_day([habit(1)], history, WEDNESDAY)["due"][0]
    assert card["streak"] == 3 and card["nudge"] == "3-day streak. Keep it going!"
    # After a break: a new start, never a scolding.
    history = {1: {WEDNESDAY - timedelta(days=5): (1, 0)}}
    card = build_day([habit(1)], history, WEDNESDAY)["due"][0]
    assert card["streak"] == 0 and card["nudge"] == "New start: day 1 today"


def test_a_rest_day_is_left_out_of_the_ring():
    day = build_day([habit(1), habit(2)], {1: {WEDNESDAY: (0, 1)}}, WEDNESDAY)
    rested = day["due"][0]
    assert rested["rested"] and rested["line"] == "Rest day" and not rested["done"]
    assert (day["done"], day["total"]) == (0, 1)


def test_a_habit_to_avoid_is_done_until_you_slip():
    soda = habit(1, avoid=1)
    day = build_day([soda], {}, WEDNESDAY)
    assert day["due"][0]["done"] and day["due"][0]["line"] == "Clean today" and (day["done"], day["total"]) == (1, 1)
    day = build_day([soda], {1: {WEDNESDAY: (1, 0)}}, WEDNESDAY)
    card = day["due"][0]
    assert card["slipped"] and not card["done"] and card["line"].startswith("Slipped today")
    assert card["streak"] == 0 and card["nudge"] is None  # the line already says "tomorrow is a new day"
    assert (day["done"], day["total"]) == (0, 1)


def test_day_sets_for_a_habit_to_avoid():
    soda = habit(1, avoid=1, start_date="2026-10-25")
    done, rest, slips = day_sets(soda, {MONDAY: (1, 0), TUESDAY: (0, 1)}, WEDNESDAY)
    assert slips == {MONDAY} and rest == {TUESDAY}
    assert done == {date(2026, 10, 25), WEDNESDAY}

def test_greetings_by_the_hour():
    assert greeting(5)[0] == "Magandang umaga"
    assert greeting(11)[0] == "Magandang umaga"
    assert greeting(12)[0] == "Magandang hapon"
    assert greeting(18)[0] == "Magandang gabi"
    assert greeting(2)[0] == "Magandang gabi"


def test_progress_messages_cheer_and_never_scold():
    assert "rest" in progress_message(0, 0)
    assert "start" in progress_message(0, 5)
    assert "4 to go" in progress_message(1, 5)
    assert "Halfway" in progress_message(3, 5)
    assert "Just 1 more" in progress_message(4, 5)
    assert "Perfect day" in progress_message(5, 5)
