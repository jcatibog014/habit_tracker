"""Gawi, a habit tracker: daily habits, streaks and completion history.

Flask builds the app inside create_app() (the "app factory" pattern).
Tests call it with their own settings, so each test gets a fresh app and database.
"""
import mimetypes
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

from flask import Flask, render_template

# Python doesn't know this file type, and browsers want the right one for
# the app manifest (the name and icons used by "Add to Home Screen").
mimetypes.add_type("application/manifest+json", ".webmanifest")

from . import messages, schedule, validation
from .dates import short_date

# One emoji font for everyone, so the icons look the same (flat and colourful)
# on Windows, Android and iPhone. "text=" asks Google Fonts for only the
# emoji we use: a few KB instead of the whole 10 MB font.
APP_EMOJI = validation.ICONS + messages.EMOJI
EMOJI_FONT_URL = (
    "https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap&text="
    + quote("".join(sorted(set(APP_EMOJI))))
)

DEV_SECRET_KEY = "dev-only-not-secret"

# Content-Security-Policy: the browser may only load scripts, styles, fonts
# and images from these places. If someone ever sneaked a <script> into a
# page (in a habit name, say), the browser would refuse to run it.
# 'unsafe-inline' for styles only: some templates set a colour or width in style="".
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self'",
    "manifest-src 'self'",
    "worker-src 'self'",  # the service worker, /sw.js
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    on_render = bool(os.environ.get("RENDER"))  # Render sets RENDER=true on its servers
    app.config.from_mapping(
        # Signs the login cookie. On Render it comes from an environment variable.
        SECRET_KEY=os.environ.get("SECRET_KEY", DEV_SECRET_KEY),
        # Local SQLite file, in the instance/ folder (git ignores it).
        DATABASE=str(Path(app.instance_path) / "gawi.sqlite"),
        # Set on the live site: then we use PostgreSQL (Neon) instead of SQLite.
        DATABASE_URL=os.environ.get("DATABASE_URL"),
        # Cookie safety: not readable by JavaScript (Flask's default), not sent
        # with forms from other sites, and only over HTTPS on the live site.
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=on_render,
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        MAX_CONTENT_LENGTH=256 * 1024,  # no uploads; forms are small
    )
    if test_config:
        app.config.update(test_config)
    if on_render and app.config["SECRET_KEY"] == DEV_SECRET_KEY:
        raise RuntimeError("Set the SECRET_KEY environment variable on Render.")
    if on_render and not app.config["DATABASE_URL"]:
        # Without it we'd use a SQLite file, and Render forgets files on every restart.
        raise RuntimeError("Set the DATABASE_URL environment variable on Render (Neon's connection string).")

    from . import auth, db
    from .views import habits, main

    db.init_app(app)
    auth.init_app(app)
    # auth comes first: its before_request (load_user) must run before the others'.
    for blueprint in (auth.bp, main.bp, habits.bp):
        app.register_blueprint(blueprint)

    app.jinja_env.filters["short_date"] = short_date
    app.jinja_env.filters["schedule"] = schedule.describe
    app.jinja_env.filters["goal"] = schedule.goal
    app.jinja_env.globals["APP_NAME"] = "Gawi"
    app.jinja_env.globals["EMOJI_FONT_URL"] = EMOJI_FONT_URL

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")  # trust our file types
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")  # no showing us inside other sites
        if on_render:
            # Always use HTTPS for this site from now on (for a year).
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return response

    def error_page(code, message):
        return render_template("error.html", code=code, message=message), code

    @app.errorhandler(400)
    def bad_request(error):
        return error_page(400, error.description or "Something in that request was wrong.")

    @app.errorhandler(403)
    def forbidden(error):
        return error_page(403, error.description or "You can't do that.")

    @app.errorhandler(404)
    def not_found(error):
        return error_page(404, "We couldn't find that page.")

    @app.errorhandler(413)
    def too_large(error):
        return error_page(413, "That was too much to send at once.")

    return app
