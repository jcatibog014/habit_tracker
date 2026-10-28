from datetime import date

from gawi.validation import habit_form_values, validate_habit

TODAY = date(2026, 10, 28)
GOOD = {
    "name": "  Drink   water ", "icon": "💧", "color": "blue", "kind": "check",
    "schedule": "daily", "weekdays": [], "start_date": "2026-10-28",
}


def check(**changes):
    return validate_habit({**GOOD, **changes}, set(), TODAY)


def test_a_good_habit():
    data, errors = check()
    assert errors == {}
    assert data["name"] == "Drink water"  # spaces tidied
    assert (data["target"], data["unit"], data["weekdays"], data["per_week"]) == (1, "", "", None)


def test_name_is_needed_and_short():
    assert "name" in check(name="   ")[1]
    assert "name" in check(name="x" * 41)[1]


def test_name_must_be_new_whatever_the_case():
    data, errors = validate_habit(GOOD, {"drink water"}, TODAY)
    assert "already" in errors["name"]


def test_icon_and_colour_come_from_the_lists():
    errors = check(icon="<script>", color="black")[1]
    assert set(errors) == {"icon", "color"}


def test_count_needs_a_goal_from_2():
    data, errors = check(kind="count", target="8", unit=" glasses ")
    assert errors == {} and (data["target"], data["unit"]) == (8, "glasses")
    assert "target" in check(kind="count", target="1")[1]
    assert "target" in check(kind="count", target="lots")[1]
    assert "target" in check(kind="count", target="1001")[1]


def test_a_yes_no_habit_ignores_the_count_fields():
    data, errors = check(kind="check", target="50", unit="pages")
    assert errors == {} and (data["target"], data["unit"]) == (1, "")


def test_weekdays_are_sorted_and_cleaned():
    data, errors = check(schedule="weekdays", weekdays=["5", "1", "3", "3", "9", "x"])
    assert errors == {} and data["weekdays"] == "1,3,5"
    assert "weekdays" in check(schedule="weekdays", weekdays=[])[1]


def test_all_seven_days_is_every_day():
    data, errors = check(schedule="weekdays", weekdays=[str(day) for day in range(1, 8)])
    assert errors == {} and data["schedule"] == "daily" and data["weekdays"] == ""


def test_times_a_week_is_1_to_6():
    assert check(schedule="weekly", per_week="3")[0]["per_week"] == 3
    assert "per_week" in check(schedule="weekly", per_week="7")[1]
    assert "per_week" in check(schedule="weekly", per_week="")[1]


def test_unknown_schedule_or_kind():
    errors = check(schedule="hourly", kind="maybe")[1]
    assert set(errors) == {"schedule", "kind"}


def test_start_date_limits():
    assert "start_date" in check(start_date="")[1]
    assert "start_date" in check(start_date="1999-12-31")[1]
    assert "start_date" in check(start_date="2027-10-29")[1]  # more than a year ahead
    assert check(start_date="2027-10-28")[1] == {}


def test_form_values_turn_a_habit_back_into_a_form():
    habit = {"kind": "check", "target": 1, "weekdays": "1,3", "per_week": None, "name": "X"}
    values = habit_form_values(habit)
    assert values["weekdays"] == ["1", "3"] and values["target"] == "" and values["per_week"] == ""
