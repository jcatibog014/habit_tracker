# AGENTS.md

This file guides AI coding agents (Claude Code, Codex, Cursor, Copilot and others) working in this repository.

## Overview

**Gawi** ("habit"), a habit tracker in Python (Flask). The repo is `habit_tracker` and the Python package is `gawi`. It tracks daily habits (yes/no or counted, every day / some weekdays / N times a week), streaks and completion history. It is a learning project for **dates, summaries and simple analytics**, so all database access is raw SQL (no ORM) and all date/streak/stats logic is pure Python that takes `today` as an argument. The roadmap is `docs/PLAN.md` (6 stages, one PR each). Keep the code readable for a learner: short comments that explain *why*, and no extra libraries unless the owner asks. Write the README in simple (A1-level) English.

Python 3.13 is at `%LOCALAPPDATA%\Programs\Python\Python313\python.exe`. Use the virtual environment:

- Install: `.venv\Scripts\python -m pip install -r requirements.txt` (create `.venv` with `python -m venv .venv` first if it's missing).
- First time: `.venv\Scripts\flask --app gawi init-db`, then `.venv\Scripts\flask --app gawi create-user <name>`.
- Run: `.venv\Scripts\flask --app gawi run --debug --port 5004`, then open http://127.0.0.1:5004. (Port 5004: Swap Meter 5000, Ambon Alert 5001, Ang Gastos! 5002, Sangkap 5003.)
- Test: `.venv\Scripts\python -m pytest`. Tests use a fresh SQLite file each and never use the internet. Set `TEST_DATABASE_URL` to an **empty** Neon branch to run the same tests on PostgreSQL (each test drops and remakes the tables).
- Other commands: `set-password <name>`, `reset-demo`, `upgrade-db`, `init-db --yes` (deletes everything).

## Architecture

Ported from `Documents\Workspace\expense_tracker` (Ang Gastos!): `db.py`, `auth.py`, the CSRF check, the demo login, `create_app()` and the tests' `conftest.py` work the same way there.

- **Two databases, one SQL.** `gawi/db.py` connects to SQLite (`instance/gawi.sqlite`, git-ignored) or, when `DATABASE_URL` is set, to PostgreSQL with psycopg (Neon live). Use `db.query()`, `query_one()`, `execute()`, `execute_many()`, `insert()` (for `INSERT ... RETURNING id`) and `commit()`. Rows come back as dicts. Write `?` placeholders; `_sql()` turns them into `%s` for psycopg. Never put values into the SQL text. Nothing is saved without `commit()`.
- Keep SQL portable: days are `'YYYY-MM-DD'` text; no `strftime()`/`to_char()`/`EXTRACT` (weekdays are worked out in Python). True/false is `0/1`. In `schema.sql`, keep the exact spelling `id INTEGER PRIMARY KEY` (rewritten for Postgres by `schema_sql()`).
- **Migrations:** `db.MIGRATIONS` (empty so far) + `upgrade_db()` / `flask --app gawi upgrade-db`, as in Gastos. To change the schema once the live database exists: edit `schema.sql` **and** add a migration at the end; never edit one that has run live.
- `gawi/schema.sql`: `users` (+ `timezone`, default `Asia/Manila`), `habits`, `checkins`.
  - `habits.kind` is `check` (target always 1) or `count` (target ≥ 2, optional `unit`). `schedule` is `daily`, `weekdays` (`weekdays` = `"1,3,5"`, Monday = 1 like `isoweekday()`) or `weekly` (`per_week` 1–6). CHECKs enforce these pairs. `start_date`: nothing before it counts. `archived_at` hides a habit but keeps its history. `position` orders the list. `UNIQUE (user_id, name)`.
  - `checkins`: one row per habit per day (`UNIQUE (habit_id, day)`), `value` (done when `value >= target`), `skipped` (a rest day), `note`. **No row means not done**; misses are never stored. There is no `user_id`: reach the owner through `JOIN habits`. Deleting a habit deletes its check-ins (`ON DELETE CASCADE`).
- **Privacy:** every query filters on `g.user["id"]` (for check-ins, via their habit). Another user's habit gives 404 (`views.owned_habit()`). Tests check that the demo can't see the owner's habits.
- **"Today"** is always `views.user_today()` = `dates.today(g.user["timezone"])`, never `date.today()` (Render runs on UTC). `dates.py` uses `zoneinfo` + the `tzdata` package (Windows has no tz database). `TIMEZONES` is the list Settings offers. Login lock times use `dates.now()` (Manila) so they compare as text.
- `gawi/auth.py`: login/logout, `POST /demo`, `/settings` (two forms on one page, told apart by a hidden `form` field: `timezone` and `password`; the demo gets 403 for both), `login_required`, `g.user` (`id`, `username`, `is_demo`, `timezone`), CLI commands. No sign-up page. 5 wrong passwords lock the account for 15 minutes. Wrong logins always say `WRONG_LOGIN`.
- **CSRF:** every POST form needs `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`. Tests use `post()` from `tests/conftest.py`.
- **The demo** (`is_demo = 1`, username `demo`, unknown random password) is reset by `seed.reset_demo()` when `demo_reset_at` is over an hour old: `DEMO_HABITS` (6 habits, one of each kind/schedule) starting `DEMO_START_DAYS_AGO` (90) days ago.
- `gawi/validation.py` (no Flask): `validate_habit(form, taken_names, today)` returns `(data, errors)`; `form["weekdays"]` is a list. All 7 weekdays become `daily`. `ICONS` (36 emoji, so the picker has full rows: 9 across, 6 on phones), `COLORS` (8 names, CSS `--habit-<name>`), `habit_form_values()` (a habit row → form values).
- `gawi/schedule.py` (no Flask): `describe(habit)` ("Every day", "Mon · Wed · Fri", "Weekdays", "3 times a week"), `goal(habit)` ("8 glasses"), `week_start(day)` (Monday) and `is_due(habit, day)` (false before `start_date`; `weekdays` checks `isoweekday()`; `weekly` is due any day). `describe`/`goal` are also Jinja filters. Stage 2 adds `due_days()` here.
- `gawi/daily.py` (no Flask, no SQL): `build_day(habits, values, week_done, day)` splits active habits into `due` and `rest` cards (`{habit, value, done, line, percent}`) and counts `done`/`total` among `due`. A weekly habit leaves `due` (with `week_reached`) once the week's goal was reached on *earlier* days; ticking it today keeps it in `due`. Habits not due today (day off, not started) are in `rest`.
- `gawi/queries.py`: `day_values(user_id, day)` (`{habit_id: value}`), `done_days_between(user_id, first, last)` (`GROUP BY habit_id`, done = `value >= h.target`, so it JOINs habits), `set_value(habit_id, day, value)` (upsert with `ON CONFLICT (habit_id, day) DO UPDATE`; 0 deletes the row).
- `gawi/messages.py` (no Flask): `greeting(hour)` (Magandang umaga/hapon/gabi + emoji) and `progress_message(done, total)`: cheering, never scolding. `EMOJI` lists every emoji used outside the habit icons (also in flash messages and templates) for the emoji font; add new ones there.
- `gawi/views/`: `main` (`/` is the **Today** page; `POST /checkin/<id>` with `action=toggle|plus|minus` for today only: 404 for archived/other users' habits, 400 before `start_date`; a habit on its day off can still be ticked. It answers JSON when the request's best Accept is `application/json` (app.js), else redirects to `/#habit-<id>`; `/healthz`), `habits` (`/habits` list + archived `<details>`, `/habits/new` (`?suggestion=<name>` fills in one of `SUGGESTIONS`), `/habits/<id>/edit`, `POST .../archive` (toggles; bringing back puts it last), `POST .../delete`, `POST /habits/reorder` (`order=3,1,2`: must be exactly the user's active habit ids, else 400; positions become 0..n-1; JSON `{ok: true}`)).

### Front end and theme

- Server-rendered Jinja pages with plain HTML forms; they work without JavaScript. `static/app.js` adds:
  - the theme toggle, `data-confirm`, closing flash messages (`data-close-flash`), and `data-show-when="kind=count"` (shows a part only while that radio is picked; without JS everything shows);
  - **check-ins** (`form[data-checkin]`): sent with `fetch()` + `Accept: application/json`, queued per card so fast taps all count. The JSON updates the card (`is-done`, `--percent`, count, `aria-pressed`/`aria-label`) and the hero ring and message. It plays `just-done` (tick pop) and, on a perfect day, `celebrate` (sun burst), and announces in `#live`. Use `form.getAttribute("action")`: the form has a field named `action`, which hides `form.action`;
  - **drag to reorder** (`[data-reorder]`, handles `[data-handle]`): pointer events on `window` (moving the item in the page would cancel pointer capture), arrow keys on a focused handle, and a save to `/habits/reorder` right away. Handles are `.js-only` (hidden without JS).
- **Today page** (`today.html`): a hero (date, greeting, cheer, and a conic-gradient **progress ring** whose `--percent` is an `@property`, so it animates), then a card per habit for today with one big round **check button** on the right (the main action). Yes/no habits toggle; counts tap +1, with a small − button, and the button's ring fills up. Done cards turn softly green and the button fills with `--done` and a `--on-done` tick (white in light mode, dark in dark mode). "Not for today" is a `<details>`. No habits = the ideas card (`empty_ideas` macro).
- **Adding a habit:** on computers, the `fab` macro is a big pill button *under* the list. Never make it float: it would cover the check buttons. On phones it hides, and a raised round **+** (`.nav-add`) sits in the middle of the bottom tab bar.
- Habit list rows: drag handle, icon, name (links to edit), and a quiet pencil `icon-button` (shows on hover/focus where hover exists, always on touch screens).
- **Demo:** a small "Demo" badge in the header (its tip shows on hover/focus; the username is hidden for the demo) instead of a banner; the welcome flash says it resets every hour.
- **Emoji font:** every emoji uses "Noto Color Emoji" (in the `--font-body`/`--font-round` stacks), loaded from Google Fonts with `text=` set to `APP_EMOJI` (`validation.ICONS` + `messages.EMOJI`), so it's a few KB. The emoji look the same (flat) on every device.
- **Theme "morning sunrise": lively but neat.** The owner wants the app to motivate people to do their habits. Lively: the sunrise gradient header (`--header-bg`), a bright colour per habit (left edge, icon bubble), round shapes (pill buttons, Fredoka headings), small happy movements (flash slides in, buttons press, the empty-state sprout grows). Neat: calm cream/white everywhere else, one spacing scale (4/8/12/16/24/32px), `--radius` 18px cards, at most ~3 accents per screen, a card shows at most 3 pieces of info. Messages are warm and never guilt-tripping (a missed day is grey `--skip`, never red).
- Fonts: Fredoka (headings, brand) and Nunito (body), from Google Fonts.
- Colours are CSS variables on `:root`. Dark mode ("early dawn": deep indigo, warm accents) redefines them under `prefers-color-scheme: dark` (unless `data-theme="light"`) and under `[data-theme="dark"]`; change both blocks together.
- Accessibility: text ≥ 4.5:1 (`--primary` #c2410c carries white text at 5.2:1), habit colours ≥ 3:1 against `--card` and never used for text, touch targets ≥ 44px, form errors use `aria-invalid` + `aria-describedby`, pickers are real radios/checkboxes styled with `:has()`. Every animation is switched off under `prefers-reduced-motion`.
- Phones (≤ 520px): the tabs become a bottom bar (icon + label); habit rows stay on one line (the Edit button hides; the name opens the editor).
- Logo: a checkmark in a rising sun, `templates/_logo.html` (header) and `static/icons/logo.svg` (favicon). Keep them the same drawing.
- **Security headers** (`create_app`): CSP (`script-src 'self'`; add cdn.jsdelivr.net when Chart.js arrives in stage 4), `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, HSTS on Render. **No inline `<script>`** (`test_no_inline_scripts`); JSON in `<script type="application/json">` is fine.

## Conventions

- One branch + PR per stage of `docs/PLAN.md`. On this Windows machine, pass commit messages and PR bodies as files (`git commit -F`, `gh pr create --body-file`).
- Add or update a test with every behaviour change. Date logic is tested with fixed dates, never the real today.
- Use sentence case for headings and buttons.
