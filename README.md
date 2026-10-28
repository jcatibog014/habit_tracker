# Gawi ☀️

**Gawi** means "habit". This app helps you build good habits, one day at a time.

- Add your habits: "Drink water", "Read", "Walk"…
- A habit can be **yes or no** ("Did I pray today?") or a **count** ("8 glasses of water").
- A habit can be for **every day**, **some days** (Mon, Wed, Fri) or **some times a week**.
- On the **Today** page, tap the big round button to tick a habit. The ring at the top shows how much of today is done.
- Drag the dots ⠿ on the Habits page to change the order.
- Soon: keep your **streak** 🔥 and see your progress over weeks and months.

The app is still being built. The plan is in [docs/PLAN.md](docs/PLAN.md).

## How to run it

You need Python 3.13.

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\flask --app gawi init-db
.venv\Scripts\flask --app gawi create-user yourname
.venv\Scripts\flask --app gawi run --debug --port 5004
```

Then open http://127.0.0.1:5004 in your browser.
To look around first, press **Try the demo** on the login page.

## How to test it

```
.venv\Scripts\python -m pytest
```
