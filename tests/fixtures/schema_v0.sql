-- The schema from before db.MIGRATIONS[0] (habits.avoid), for test_upgrade_an_old_database.
-- The tables of Gawi. This SQL runs on SQLite and on PostgreSQL.
-- (db.schema_sql() changes the "id INTEGER PRIMARY KEY" lines for Postgres.)
--
-- Dates are text in ISO order: '2026-10-28'. Text in this order sorts like
-- the dates themselves, so SQL can use <, >, BETWEEN and ORDER BY on it.
-- True/false is 1/0, which both databases understand.

-- Children before parents: a table can't be dropped while another one points at it.
DROP TABLE IF EXISTS schema_version;
DROP TABLE IF EXISTS checkins;
DROP TABLE IF EXISTS habits;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0,
    demo_reset_at TEXT,                 -- when the demo data was last made fresh
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,                  -- too many wrong passwords: wait until then
    -- "Today" starts at midnight in this time zone. The server runs on UTC,
    -- so without it a Manila day would start at 8 AM.
    timezone TEXT NOT NULL DEFAULT 'Asia/Manila'
);

CREATE TABLE habits (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    icon TEXT NOT NULL,                  -- an emoji, from validation.ICONS
    color TEXT NOT NULL,                 -- a colour name, from validation.COLORS
    -- 'check': done or not done. 'count': done when the day's count reaches
    -- the target (8 glasses of water). A check habit's target is always 1.
    kind TEXT NOT NULL CHECK (kind IN ('check', 'count')),
    target INTEGER NOT NULL DEFAULT 1 CHECK (target >= 1),
    unit TEXT NOT NULL DEFAULT '',
    -- 'daily': every day. 'weekdays': only the days in `weekdays`
    -- ('1,3,5' = Mon, Wed, Fri; Monday is 1). 'weekly': any `per_week` days a week.
    schedule TEXT NOT NULL CHECK (schedule IN ('daily', 'weekdays', 'weekly')),
    weekdays TEXT NOT NULL DEFAULT '',
    per_week INTEGER CHECK (per_week BETWEEN 1 AND 6),
    start_date TEXT NOT NULL,            -- nothing before this day counts
    archived_at TEXT,                    -- hidden but kept (with its history) when set
    position INTEGER NOT NULL DEFAULT 0, -- the order on the page
    created_at TEXT NOT NULL,
    CHECK (kind = 'count' OR target = 1),
    CHECK (schedule <> 'weekdays' OR weekdays <> ''),
    CHECK (schedule <> 'weekly' OR per_week IS NOT NULL),
    UNIQUE (user_id, name)
);

-- One row per habit per day, and only for days with something to remember.
-- No row means "not done": misses are worked out from the schedule, never stored.
-- There is no user_id here: a check-in belongs to whoever owns its habit,
-- so queries reach the user through JOIN habits.
CREATE TABLE checkins (
    id INTEGER PRIMARY KEY,
    habit_id INTEGER NOT NULL REFERENCES habits (id) ON DELETE CASCADE,
    day TEXT NOT NULL,
    value INTEGER NOT NULL DEFAULT 0 CHECK (value >= 0),  -- done when value >= the habit's target
    skipped INTEGER NOT NULL DEFAULT 0,  -- a rest day: it doesn't break a streak or lower the score
    note TEXT NOT NULL DEFAULT '',
    -- One row per day. This also gives the database an index on (habit_id, day),
    -- which every "check-ins between these days" query uses.
    UNIQUE (habit_id, day)
);

-- Which upgrades (db.MIGRATIONS) this database already has. See db.upgrade_db().
CREATE TABLE schema_version (
    version INTEGER NOT NULL
);
