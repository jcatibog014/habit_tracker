"""The home page and the health check."""
from flask import Blueprint, redirect, url_for

from ..auth import login_required

bp = Blueprint("main", __name__)


@bp.get("/healthz")
def health():
    """Render calls this to check the site is up. No login and no database, so it's quick."""
    return {"status": "ok"}


@bp.get("/")
@login_required
def home():
    # The Today page comes in stage 2. Until then, home is the habit list.
    return redirect(url_for("habits.index"))
