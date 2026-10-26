"""The admin learner overview: support-oriented, aggregate, and deliberately thin. There is no impersonation here or anywhere (no "log in as", no session issued
for a learner), and nothing identifying: no name, email, password or hash, session, date of birth, message, transcript, recording or parent link.

  * A learner is named only by an opaque reference: an HMAC (key: settings.admin_ref_secret()) of their id. The raw id never leaves the repository/service layer,
    and a reference cannot be turned back into an id without the key.
  * Small cells: the list and the detail view are withheld (suppressed) while fewer than SMALL_CELL learners are involved: the filtered list needs at least 5
    learners in it, the detail view at least 5 learners on the platform. Within a response, a learner's target language, CEFR level and age band are shown only if at
    least 5 learners share that exact combination; otherwise they are null, so a lone teen learning Hindi at B2 cannot be picked out by the attributes.
  * Dates are dates (no time), counts are counts."""
import hashlib
import hmac
from datetime import timedelta

from .. import settings
from ..db import connect
from ..repositories import admin_learners as repo
from . import analytics
from .errors import InvalidInput, NotFound

SMALL = settings.SMALL_CELL


def ref_for(user_id):
    return hmac.new(settings.admin_ref_secret(), f"learner:{user_id}".encode(), hashlib.sha256).hexdigest()[:32]


def _generalise(row, cells):
    """The attributes of a learner, or nulls when too few learners share them."""
    key = (row["language"], row["cefr"], row["age_group"])
    if cells.get(key, 0) < SMALL:
        return {"language": None, "cefr": None, "age_group": None}
    return {"language": row["language"], "cefr": row["cefr"], "age_group": row["age_group"]}


def list_learners(db_path, language, cefr, age_group, active_since, limit, offset):
    if active_since:
        try:
            from datetime import date
            date.fromisoformat(active_since)
        except ValueError:
            raise InvalidInput("active_since", "dates are YYYY-MM-DD")
    today = analytics.utcnow().date().isoformat()
    with connect(db_path) as conn:
        total, ids = repo.list_ids(conn, settings.DEMO_HANDLE, today, language, cefr, age_group, active_since, limit, offset)
        if total < SMALL:
            return {"suppressed": True, "total": None, "items": [], "limit": limit, "offset": offset}
        rows = repo.summary_rows(conn, settings.DEMO_HANDLE, today, ids)
        cells = repo.cell_sizes(conn, settings.DEMO_HANDLE, today)
    items = []
    for uid in ids:
        r = rows[uid]
        items.append({"ref": ref_for(uid), **_generalise(r, cells), "joined": r["joined"], "last_active": r["last_active"], "lessons_completed": r["lessons_completed"],
                      "situations_completed": r["situations_completed"], "exercise_attempts": r["exercise_attempts"]})
    return {"suppressed": False, "total": total, "items": items, "limit": limit, "offset": offset}


def get_learner(db_path, ref):
    today = analytics.utcnow().date()
    with connect(db_path) as conn:
        everyone = repo.all_ids(conn, settings.DEMO_HANDLE)
        match = next((uid for uid in everyone if hmac.compare_digest(ref_for(uid), ref)), None)
        if match is None:
            raise NotFound()
        if len(everyone) < SMALL:
            return {"suppressed": True, "ref": ref}
        row = repo.summary_rows(conn, settings.DEMO_HANDLE, today.isoformat(), [match])[match]
        cells = repo.cell_sizes(conn, settings.DEMO_HANDLE, today.isoformat())
        counts = repo.detail_counts(conn, match, f"{(today - timedelta(days=29)).isoformat()} 00:00:00")
    return {"suppressed": False, "ref": ref, **_generalise(row, cells), "joined": row["joined"], "last_active": row["last_active"], "totals": counts}
