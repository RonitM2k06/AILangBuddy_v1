"""Admin views of accounts and security events (Phase 14E). Admin role + MFA session only (the admin router's admin_only).

  * Accounts: the replacement for the Phase 2 user listing, which returned every account's e-mail, name and handle. Now: an opaque
    reference (the same HMAC reference the learner overview uses, backend/admin/learners.ref_for), roles, the account's creation date and
    whether two-factor authentication is on. Paginated (limit/offset, at most 100), oldest first by account.
  * Security events: newest first, by an opaque cursor; optionally one event type from the closed list. Each event shows only its closed
    fields; the account appears as its HMAC reference and the network as the stored 16-hex HMAC. There is no free-text search and no
    filter by account or address, so the view cannot be turned into a lookup of a particular person."""
from ..db import connect
from ..repositories import security_events as repo
from .learners import ref_for

MAX_PAGE = 100


def accounts(db_path, limit, offset):
    with connect(db_path) as conn:
        total = repo.count_accounts(conn)
        rows = repo.page_accounts(conn, limit, offset)
    items = [{"ref": ref_for(r["id"]), "roles": r["roles"].split(",") if r["roles"] else [], "created": r["created_at"][:10], "two_factor": bool(r["two_factor"])}
             for r in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def security_events(db_path, limit, before, event_type):
    with connect(db_path) as conn:
        rows = repo.page_events(conn, before, event_type, limit)
    more = len(rows) > limit
    rows = rows[:limit]
    items = [{"occurred_at": r["occurred_at"], "type": r["event_type"], "outcome": r["outcome"], "account": ref_for(r["user_id"]) if r["user_id"] is not None else None,
              "method": r["method"], "reason": r["reason"], "stage": r["stage"], "count": r["count"], "network": r["ip_ref"]} for r in rows]
    return {"items": items, "limit": limit, "next": str(rows[-1]["id"]) if more and rows else None}
