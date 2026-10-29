from gawi import db

from .conftest import HABIT_FORM, add_habit, get_habit, post


def habit_names(app, user_id):
    with app.app_context():
        rows = db.query(
            "SELECT name FROM habits WHERE user_id = ? AND archived_at IS NULL ORDER BY position, id",
            (user_id,),
        )
        return [row["name"] for row in rows]


def test_empty_list_shows_ideas(owner_client):
    page = owner_client.get("/habits").get_data(as_text=True)
    assert "Start with one small habit" in page
    assert "/habits/new?suggestion=Drink+water" in page


def test_an_idea_fills_in_the_form(owner_client):
    page = owner_client.get("/habits/new?suggestion=Drink+water").get_data(as_text=True)
    assert 'value="Drink water"' in page and 'value="glasses"' in page and 'value="8"' in page


def test_add_a_habit(owner_client, app, owner_id):
    response = post(owner_client, "/habits/new", HABIT_FORM)
    assert response.status_code == 302 and response.headers["Location"] == "/habits"
    page = owner_client.get("/habits").get_data(as_text=True)
    assert "Read" in page and "Every day" in page and "is on your list" in page


def test_add_a_counted_habit_on_some_days(owner_client, app, owner_id):
    form = {**HABIT_FORM, "name": "Water", "kind": "count", "target": "8", "unit": "glasses",
            "schedule": "weekdays", "weekdays": ["1", "3", "5"]}
    post(owner_client, "/habits/new", form)
    with app.app_context():
        habit = db.query_one("SELECT * FROM habits WHERE name = 'Water'")
    assert (habit["kind"], habit["target"], habit["unit"]) == ("count", 8, "glasses")
    assert (habit["schedule"], habit["weekdays"]) == ("weekdays", "1,3,5")
    page = owner_client.get("/habits").get_data(as_text=True)
    assert "Mon · Wed · Fri · 8 glasses" in page


def test_the_form_shows_what_is_wrong(owner_client):
    response = post(owner_client, "/habits/new", {**HABIT_FORM, "name": "", "schedule": "weekly", "per_week": "9"})
    page = response.get_data(as_text=True)
    assert response.status_code == 400
    assert "Give your habit a name." in page and "from 1 to 6" in page


def test_two_habits_cannot_share_a_name(owner_client, app, owner_id):
    add_habit(app, owner_id, "Read")
    response = post(owner_client, "/habits/new", {**HABIT_FORM, "name": "READ"})
    assert response.status_code == 400
    assert "already have a habit" in response.get_data(as_text=True)


def test_new_habits_go_to_the_end_of_the_list(owner_client, app, owner_id):
    post(owner_client, "/habits/new", {**HABIT_FORM, "name": "First"})
    post(owner_client, "/habits/new", {**HABIT_FORM, "name": "Second"})
    assert habit_names(app, owner_id) == ["First", "Second"]


def test_edit_a_habit(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Read")
    page = owner_client.get(f"/habits/{habit_id}/edit").get_data(as_text=True)
    assert 'value="Read"' in page

    response = post(owner_client, f"/habits/{habit_id}/edit",
                    {**HABIT_FORM, "name": "Read a book", "schedule": "weekly", "per_week": "3"})
    assert response.status_code == 302
    habit = get_habit(app, habit_id)
    assert (habit["name"], habit["schedule"], habit["per_week"]) == ("Read a book", "weekly", 3)


def test_editing_can_keep_the_same_name(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Read")
    response = post(owner_client, f"/habits/{habit_id}/edit", {**HABIT_FORM, "name": "Read"})
    assert response.status_code == 302


def test_archive_and_bring_back(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Read")
    post(owner_client, f"/habits/{habit_id}/archive")
    assert get_habit(app, habit_id)["archived_at"] is not None
    page = owner_client.get("/habits").get_data(as_text=True)
    assert "Archived (1)" in page

    post(owner_client, f"/habits/{habit_id}/archive")
    assert get_habit(app, habit_id)["archived_at"] is None


def test_delete_removes_the_habit_and_its_check_ins(owner_client, app, owner_id):
    habit_id = add_habit(app, owner_id, "Read")
    with app.app_context():
        db.execute("INSERT INTO checkins (habit_id, day, value) VALUES (?, '2026-10-02', 1)", (habit_id,))
        db.commit()
    post(owner_client, f"/habits/{habit_id}/delete")
    assert get_habit(app, habit_id) is None
    with app.app_context():
        assert db.query("SELECT * FROM checkins WHERE habit_id = ?", (habit_id,)) == []


def test_the_list_has_drag_handles_and_pencils(owner_client, app, owner_id):
    add_habit(app, owner_id, "Read")
    page = owner_client.get("/habits").get_data(as_text=True)
    assert "data-handle" in page and 'aria-label="Edit Read"' in page and 'class="fab"' in page


def test_reorder_by_dragging(owner_client, app, owner_id):
    a = add_habit(app, owner_id, "A", position=0)
    b = add_habit(app, owner_id, "B", position=1)
    c = add_habit(app, owner_id, "C", position=2)
    response = post(owner_client, "/habits/reorder", {"order": f"{c},{a},{b}"})
    assert response.get_json() == {"ok": True}
    assert habit_names(app, owner_id) == ["C", "A", "B"]


def test_reorder_must_name_exactly_your_habits(owner_client, app, owner_id, other_id):
    a = add_habit(app, owner_id, "A", position=0)
    b = add_habit(app, owner_id, "B", position=1)
    pedro = add_habit(app, other_id, "Pedro's")
    for bad in (f"{a}", f"{a},{b},{pedro}", f"{b},{pedro}", "x,y", ""):
        assert post(owner_client, "/habits/reorder", {"order": bad}).status_code == 400
    assert habit_names(app, owner_id) == ["A", "B"]


def test_nobody_can_touch_another_users_habit(owner_client, app, other_id):
    habit_id = add_habit(app, other_id, "Pedro's secret")
    assert owner_client.get(f"/habits/{habit_id}/edit").status_code == 404
    assert post(owner_client, f"/habits/{habit_id}/edit", HABIT_FORM).status_code == 404
    assert post(owner_client, f"/habits/{habit_id}/archive").status_code == 404
    assert post(owner_client, f"/habits/{habit_id}/delete").status_code == 404
    assert get_habit(app, habit_id)["name"] == "Pedro's secret"
