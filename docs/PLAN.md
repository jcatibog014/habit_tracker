# Roadmap: "Gawi", a habit tracker

Plan drafted on 2026-10-28. Each stage is one branch and one pull request.

## Context

This is a new learning project in the repo https://github.com/jcatibog014/habit_tracker, which has only a README so far.
It tracks daily habits, streaks and completion history. The skills to practise are **dates, summaries and simple analytics**.
It follows the conventions of the other Workspace apps: Flask, plain-function modules, pytest, `.venv`, `AGENTS.md` + `CLAUDE.md`, one PR per stage, and a Render deploy.
The login, demo, CSRF, migrations, SQLite/Neon switch and deploy setup are **ported from `Documents\Workspace\expense_tracker`** (Ang Gastos!), which is finished and live.
Another session is building `recipe_organizer` in parallel, so this app gets its own folder and never touches that one.

What the owner decided:
- The name is **"Gawi"** ("habit").
- **Habit types**: yes/no, **counted** goals (8 glasses of water) and **schedules** (every day, chosen weekdays, or N times a week).
- **Raw SQL** (no ORM), as in Ang Gastos!. Summaries are hand-written `GROUP BY` / date queries.
- **Login**: the owner + a self-resetting **demo** with about 90 days of sample history. It goes live on **Render + Neon**.

## Stack

- Python 3.13, Flask 3, Jinja server-rendered forms. A small `app.js` handles the one-tap check-ins (fetch + CSRF, no page reload), the +/− counters and the charts.
- `sqlite3` locally and in tests, `psycopg[binary]` live (when `DATABASE_URL` is set), with portable SQL: dates are `'YYYY-MM-DD'` text, `substr(day,1,7)` gives the month, and `ON CONFLICT` upserts. All of this is ported from Gastos.
- `zoneinfo` + the **`tzdata`** package. Windows has no built-in time-zone data, and Render runs on UTC, so "today" must come from the user's time zone (default `Asia/Manila`), never from `date.today()`.
- Charts: **Chart.js 4** (pinned, as in Gastos `charts.py`) for line and bar charts. The **calendar heatmap** is a server-rendered CSS grid with no library, and every chart has a "Show as table" view.
- Tests: pytest. Deploy: Render (Singapore) + Neon (Singapore). The local port is **5004** (5000 Swap Meter, 5001 Ambon Alert, 5002 Ang Gastos!, 5003 Sangkap).

## Folder and package layout

`C:\Users\USER\Documents\Workspace\habit_tracker` (a clone of the repo). The package is `gawi`.

```
gawi/
  __init__.py      create_app(test_config), error handlers, CLI (create-user, set-password, reset-demo, upgrade-db)
  db.py            SQLite/Postgres connection, MIGRATIONS list, upgrade-db   (port from gastos/db.py)
  auth.py          login/logout, login_required, csrf, demo login, lock-out  (port from gastos/auth.py)
  dates.py         today_for(user), week/month ranges, ISO weeks, parsing   (start from gastos/dates.py)
  schedule.py      is_due(habit, day), due_days(habit, start, end), week targets   (pure Python)
  streaks.py       current_streak, longest_streak, streak history           (pure Python, the main lesson)
  stats.py         completion rates, by-weekday, monthly summary, heatmap data, best/worst habit
  queries.py       ALL the SQL (check-ins in a range, totals per month/habit/day)
  validation.py    form -> (data, errors); no Flask import
  seed.py          demo habits + 90 days of history (seeded random, so it's repeatable)
  views/           blueprints: today, week, habits, stats, settings
  templates/ static/ (style.css, app.js, icons/)
tests/             conftest.py (temp SQLite, logged-in client, a fixed "today"), test_*.py
docs/PLAN.md       this roadmap; docs/screenshots/
AGENTS.md, CLAUDE.md, README.md (A1 English), render.yaml, requirements.txt
```

The design rule is that **all date and analytics logic is pure Python** that takes `today` as an argument. Tests can then freeze any date, for example a leap day, a year end or a Sunday.

## Data model

| Table | Key columns | Notes |
|---|---|---|
| `users` | id, username UNIQUE, password_hash, is_demo, demo_reset_at, failed_logins, locked_until, **timezone** | As in Gastos, plus a time zone |
| `habits` | id, user_id, name, icon (emoji), color, **kind** (`check`/`count`), **target** (1 for check), unit ("glasses"), **schedule** (`daily`/`weekdays`/`weekly`), **weekdays** ("1,3,5", Mon=1), **per_week** (N), **start_date**, archived_at, position, created_at | |
| `checkins` | id, habit_id, **day**, **value**, **skipped**, note, UNIQUE(habit_id, day) | One row per habit per day. Done means `value >= target` |

Decisions to write down (and test):
- **No row means "not done".** The app never stores misses, only check-ins. A "missed" day is a due day with no row, worked out from the schedule.
- **Skip day** (sick, travelling): `skipped = true` doesn't break the streak and doesn't extend it. It also isn't counted in the completion rate.
- **Today is still open.** If today isn't done yet, the current streak counts up to yesterday and isn't broken.
- **Days that aren't due are ignored.** For a Mon/Wed/Fri habit, the streak goes Fri → Wed → Mon. Weekends don't break it.
- **"N times a week" streaks count in weeks** (ISO weeks, Monday start). A week counts when it has ≥ N done days. The current week doesn't break the streak while it can still be reached.
- **Nothing counts before `start_date`**, so a habit started yesterday is not "3% complete for the year".
- **Editing a schedule changes the past too.** History is re-read with the new schedule. This is simple and it's written down; per-period schedule versions are in "Ideas for later".
- **Archiving** hides a habit but keeps its history and stats. **Deleting** removes its check-ins.
- Past days can be edited (forgot to tick yesterday), but future days can't.

## Features and layout (by page)

Tabs: **Today · Week · Habits · Stats · Settings** (as in Gastos, with a bottom tab bar on phones).

- **Login**: username + password, plus a **"Try the demo"** button (demo data resets after an hour, as in Gastos).
- **Today (home)**: the date and a **progress ring** ("3 of 5 done"). Below it are the habits that are due today, as large cards. Each card has the emoji, the name, a 🔥 streak badge and a **one-tap check button**. Counted habits get a **− 3/8 +** counter instead. Below that is a collapsed **"Not due today"** section. Swipe or arrows go to the previous day to fix it. When everything is done there's a **"Perfect day!"** message.
- **Week**: a grid of habits (rows) × Mon–Sun (columns). Each cell is ✓ / count / skip / empty / not due (greyed). Tap a cell to change it. The week's % is shown per row and per column, with ‹ › to move between weeks.
- **Habits**: the list (drag or ↑↓ to reorder), archived habits in their own section, and **Add / edit habit**: name, emoji picker, colour (8 swatches), yes/no or count (target + unit), schedule (daily / pick weekdays / N per week) and start date.
- **Habit page** (click a habit): **stat cards** for current streak, longest streak, 30-day completion %, all-time %, total done and total count ("1,240 glasses"). A **year heatmap** (GitHub-style, in the habit's colour), a **month calendar** where past days can be edited, a **by weekday** bar chart ("You miss Saturdays most") and recent notes. **Milestones** come at 7 / 30 / 100 / 365 days.
- **Stats**: a range picker (this week / month / 30 days / year). It shows the **overall completion % trend** per week as a line chart, the **best and worst habits**, the **best day of the week**, a leaderboard of top streaks, the number of **perfect days**, and a **monthly summary** card ("October: 82% done, 14 perfect days, best: Read 📚, longest streak: 21"). Every chart has a table view.
- **Settings**: change password, time zone, **CSV export** of all check-ins, delete or archive habits.

## Theme: morning sunrise, lively but neat (chosen by the owner)

The goal is that the app **makes you want to get up and do your habits**. It should feel bright and energetic, but stay calm and tidy, never cluttered.

**Colours and type**
- The background is warm cream with a soft **sunrise gradient** (peach → gold) only in the header and on the Today progress ring. Everything else is calm cream or white cards, so the colour stays special.
- The main colour is **sunrise orange**. Done is **fresh leaf green**, the streak flame is **amber**, and skip is a soft grey (never red, so a missed day doesn't feel like a punishment).
- Each habit has its own bright colour (8 swatches that all pass contrast) on its card edge, heatmap and badge.
- The heading font is rounded and friendly (**Fredoka**, as in Ambon Alert). The body font is clean and readable (for example **Nunito**).
- Dark mode is **"early dawn"**: deep indigo with the same warm accents, not a flat grey.

**Neat: rules that keep it tidy**
- One clear action per card (the big check button). Stats are hidden behind a tap on the habit and not packed onto Today.
- A spacing scale (4/8/16/24/32px), one corner radius, soft shadows, and lots of white space. A card shows at most 3 pieces of info (name, streak, progress).
- Only 3 accent colours on any one screen besides the habit colours. Icons come from one consistent set, and emojis are used only for habit icons.

**Lively: things that motivate you**
- **A greeting that changes with the time**: "Magandang umaga! ☀️ 4 habits waiting" in the morning, "Kaya mo 'yan, 2 left" in the afternoon, "Perfect day! 🌅" when everything is done.
- **Check-in feedback**: the button pops and fills green, the card gives a small bounce, the progress ring fills smoothly and the streak number counts up. It's quick (≤ 300ms) and it never blocks the next tap.
- **A celebration for a perfect day** (small sun rays or a confetti burst) and **milestone badges** (7 / 30 / 100 / 365 days) with a short message such as "🔥 30 days of Read! Ang galing!".
- **Gentle nudges, never guilt**: "Your streak is 12 days, keep it alive today!" on habits that are due and not done. After a break it says "New start! Day 1 🌱" instead of showing a "0".
- **Progress you can see**: the heatmap grows greener, and "Best week ever!" appears when this week beats the old record.
- **Good habits first**: Today puts the habits with the longest streaks and the ones not yet done at the top, so the next easy win is always in view.
- Every animation respects `prefers-reduced-motion`. With reduced motion turned on, it falls back to a colour change.

**Access**: contrast is ≥ 4.5:1, touch targets are ≥ 44px (the check button is 56px), and the phone breakpoint is 520px. The app is built for phones first, since habits are ticked on the go. The logo is a checkmark inside a rising sun.

## Stages (one branch + PR each)

1. **Setup, login, habits.** Clone into `Workspace\habit_tracker`, create the `.venv`, and port `db.py` / `auth.py` / CSRF / demo login / lock-out / CLI from Gastos. Add the `users`, `habits` and `checkins` tables, the base layout and tabs, and **habit CRUD** (add / edit / archive / reorder) with validation. Commit AGENTS.md, CLAUDE.md and this PLAN.md. Tests: auth, privacy (the demo gets 404 on the owner's habits) and validation.
   - **UI/UX refresh (PR #2, after stage 1).** This came from a design review. It brought forward the **Today** page with one-tap check / counters (a JSON endpoint + fetch), `schedule.is_due`, `daily.py`, `messages.py`, and the progress ring. It also added drag-to-reorder (in place of the arrows), a pencil icon (in place of the Edit button), a demo badge (in place of the banner), the "+" button (a raised one in the phone tab bar; a button under the list on computers, so it never covers a check button), and one emoji font (Noto Color Emoji) for every device.
2. **Dates, schedules, check-ins.** `dates.py` (ISO weeks, month ranges) and `schedule.py` (due_days, weekly targets), each with many unit tests. Add skip days, the **Week** grid and editing past days (Today's arrows to the previous days).
3. **Streaks.** `streaks.py` covers current and longest streaks for daily, weekday and N-per-week habits, with skips, today still open and start_date. There's a table of edge-case tests (month end, year end, leap day, Sunday→Monday). Add the habit page with stat cards, the month calendar and milestones.
4. **Summaries and analytics.** `queries.py` (GROUP BY by habit / month / day) and `stats.py` (completion %, by weekday, best/worst, perfect days, monthly summary). Add the **Stats** page, the year heatmap and the Chart.js charts with table views. The tests use a fixed set of check-ins with exact expected numbers.
5. **Demo data and motivation.** About 6 demo habits with 90 days of realistic history (weekends missed more often, one broken streak, one long streak) and demo reset. Add the motivation layer from the theme: greetings by time of day, check-in animations, the perfect-day celebration, milestone badges, gentle nudges and "Best week ever". The messages live in one `messages.py`, which is pure and tested. Also add notes on check-ins and CSV export.
6. **Polish and go live.** Icons, theme polish, security headers + CSP, `/healthz`, `render.yaml` (`upgrade-db` before gunicorn) and the README (A1 English, screenshots, tools table). The owner sets up the Neon project and the Render service `gawi` with step-by-step guidance.

Commit messages and PR bodies go through files (`git commit -F`, `gh pr create --body-file`), per the PowerShell note.

## README with screenshots

The README uses simple (A1) English: what the app does, screenshots, how to run it, the demo, and a tools table (Python, Flask, SQLite, PostgreSQL/Neon, Chart.js, Render).
The screenshots go in `docs/screenshots/` and are taken as the **demo** user: `login`, `today` (+ dark), `week`, `habit` (heatmap + streak), `stats`, `edit-habit`, `phone`. Each PR adds the screenshots for the pages it built.

## Verification

- `.venv\Scripts\python -m pytest`: pure-function tests for dates, schedules, streaks and stats (all with a fixed `today`), SQL query tests with exact totals, and view tests (login required, CSRF on check-ins, privacy between users, no future check-ins).
- Optional: `TEST_DATABASE_URL=<Neon test branch>` runs the same suite on Postgres.
- Manual: `.venv\Scripts\flask --app gawi run --debug --port 5004`. Add one habit of each type, tick today, fix yesterday, check that the streaks and stats match by hand, and check light/dark and phone width.

## Ideas for later

- Reminders (browser push notifications).
- Schedule versions, so a schedule change keeps the old history as it was.
- A "streak freeze" token earned every 7 days.
- Time-of-day groups (morning / evening).
- ~~Habits that should be avoided ("no soda")~~: done in the extra-features PR.
- ~~Make it installable on a phone (PWA)~~: done in the extra-features PR.

## Extra features PR (after PR #5)

The owner picked these from a list: streaks + a habit page (with a calendar to fix past days), rest days, milestones, gentle nudges, habits to avoid, installing on a phone (PWA), and a motivational quote of the day. They asked for it all in one PR. This brought forward much of stages 3 and 5 (`streaks.py`, the habit page, the demo history). The week grid and the Stats page (stage 4) are still to come.
