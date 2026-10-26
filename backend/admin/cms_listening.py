"""The curriculum CMS, part 3: listening activities and their options. Same edit protocol as lessons (see cms.py).
An activity offers exactly LISTENING_OPTION_COUNT options once published; a draft may hold fewer while it is being built."""
import sqlite3

from ..db import connect
from ..repositories import admin_content as repo
from . import audit, rules
from .cms import MAX_PROSE, MAX_TITLE, _constraint, load_for_edit, log, save_edit
from .errors import Conflict, InvalidInput, NotFound


def activity_detail(conn, activity_id):
    snap = repo.load_listening_activity(conn, activity_id)
    if snap is None:
        raise NotFound()
    row = repo.unit_row(conn, "listening_activity", activity_id)
    items = snap["items"]
    return {
        "id": snap["id"], "slug": snap["slug"], "language": repo.unit_languages(conn, row), "cefr": snap["cefr_code"], "title": snap["title"], "mode": snap["mode"], "prompt": snap["prompt"],
        "difficulty": snap["difficulty"], "topic": snap["topic"]["slug"] if snap["topic"] else None, "sort_order": snap["sort_order"], "status": snap["status"], "revision": snap["revision"],
        "published_at": snap["published_at"], "archived_at": snap["archived_at"], "updated_at": snap["updated_at"], "age_groups": repo.age_group_codes(conn, "listening_activity", activity_id),
        "target": {"item_id": snap["item_id"], "text": items.get(snap["item_id"], {}).get("text"), "meaning_en": items.get(snap["item_id"], {}).get("meaning_en")},
        "options": [{"id": o["id"], "item_id": o["item_id"], "sort_order": o["sort_order"], "text": items.get(o["item_id"], {}).get("text"),
                     "meaning_en": items.get(o["item_id"], {}).get("meaning_en"), "is_target": o["item_id"] == snap["item_id"]} for o in snap["options"]],
    }


def list_activities(db_path, status, language, cefr, q, limit, offset):
    with connect(db_path) as conn:
        language_id = None
        if language:
            lang = repo.language_by_code(conn, language)
            if lang is None:
                return 0, []
            language_id = lang["id"]
        return repo.list_units(conn, "listening_activity", status, language_id, cefr, q, limit, offset, repo.LISTENING_COUNTS)


def get_activity(db_path, activity_id):
    with connect(db_path) as conn:
        return activity_detail(conn, activity_id)


def _topic(conn, slug):
    tid = repo.topic_id(conn, slug)
    if tid is None:
        raise InvalidInput("topic", f"Unknown topic: {slug}")
    return tid


def create_activity(db_path, actor, rid, body):
    with connect(db_path) as conn:
        language_id = rules.language_id(repo, conn, body.language)
        rules.check_level(repo, conn, language_id, body.cefr)
        slug = rules.clean_slug("slug", body.slug)
        if repo.slug_taken(conn, "listening_activity", language_id, slug):
            raise Conflict("slug_taken", "Another listening activity in this language already uses that slug.")
        rules.vocabulary_item(repo, conn, body.item_id, language_id)
        f = {"language_id": language_id, "cefr": body.cefr, "slug": slug, "topic_id": _topic(conn, body.topic), "item_id": body.item_id,
             "title": rules.clean_text("title", body.title, MAX_TITLE), "mode": body.mode, "prompt": rules.clean_text("prompt", body.prompt, MAX_PROSE, multiline=True),
             "difficulty": rules.clean_difficulty("difficulty", body.difficulty, 3)}
        groups = rules.age_group_ids(repo, conn, body.age_groups)
        f["sort_order"] = body.sort_order if body.sort_order is not None else repo.next_sort(conn, "listening_activity", language_id, body.cefr)
        if repo.sort_taken(conn, "listening_activity", language_id, body.cefr, f["sort_order"]):
            raise Conflict("sort_order_taken", "Another listening activity at this level already has that position.")
        try:
            aid = repo.insert_activity(conn, f, rules.now())
        except sqlite3.IntegrityError as exc:
            _constraint(exc)
        repo.set_age_groups(conn, "listening_activity", aid, groups)
        audit.record(conn, actor, "create", "listening_activity", aid, slug, {"revision_after": 1}, request_id=rid)
        return activity_detail(conn, aid)


def update_activity(db_path, actor, rid, activity_id, body):
    fields = body.model_fields_set - {"revision"}
    with connect(db_path) as conn:
        row = load_for_edit(conn, "listening_activity", activity_id, body.revision, "listening activity")
        new = {}
        if "slug" in fields:
            new["slug"] = rules.clean_slug("slug", body.slug)
            if new["slug"] != row["slug"] and repo.slug_taken(conn, "listening_activity", row["language_id"], new["slug"], activity_id):
                raise Conflict("slug_taken", "Another listening activity in this language already uses that slug.")
        if "cefr" in fields:
            rules.check_level(repo, conn, row["language_id"], body.cefr)
            new["cefr_code"] = body.cefr
        if "topic" in fields:
            new["topic_id"] = _topic(conn, body.topic)
        if "item_id" in fields:
            rules.vocabulary_item(repo, conn, body.item_id, row["language_id"])
            new["item_id"] = body.item_id
        if "title" in fields:
            new["title"] = rules.clean_text("title", body.title, MAX_TITLE)
        if "mode" in fields:
            new["mode"] = body.mode
        if "prompt" in fields:
            new["prompt"] = rules.clean_text("prompt", body.prompt, MAX_PROSE, multiline=True)
        if "difficulty" in fields:
            new["difficulty"] = rules.clean_difficulty("difficulty", body.difficulty, 3)
        if "sort_order" in fields:
            new["sort_order"] = body.sort_order
        cefr_after, sort_after = new.get("cefr_code", row["cefr_code"]), new.get("sort_order", row["sort_order"])
        if (cefr_after, sort_after) != (row["cefr_code"], row["sort_order"]) and repo.sort_taken(conn, "listening_activity", row["language_id"], cefr_after, sort_after, activity_id):
            raise Conflict("sort_order_taken", "Another listening activity at this level already has that position.")
        groups = rules.age_group_ids(repo, conn, body.age_groups) if "age_groups" in fields else None
        names = {"cefr_code": "cefr", "topic_id": "topic", "item_id": "item"}
        changed = [names.get(k, k) for k, v in new.items() if row[k] != v]
        locked = [k for k in ("item_id", "mode", "difficulty") if k in new and new[k] != row[k]]
        if locked and repo.activity_has_attempts(conn, activity_id):
            raise Conflict("activity_in_use", f"Learners have answered this activity, so its {names.get(locked[0], locked[0])} cannot change.")
        current_groups = sorted(r[0] for r in conn.execute("SELECT age_group_id FROM listening_activity_age_groups WHERE activity_id = ?", (activity_id,)))
        if groups is not None and sorted(groups) != current_groups:
            changed.append("age_groups")
        if not changed:
            return activity_detail(conn, activity_id)
        revision = save_edit(conn, "listening_activity", activity_id, body.revision, "listening activity")
        try:
            repo.update_fields(conn, "listening_activity", activity_id, {k: v for k, v in new.items() if row[k] != v})
        except sqlite3.IntegrityError as exc:
            _constraint(exc)
        if "age_groups" in changed:
            repo.set_age_groups(conn, "listening_activity", activity_id, groups)
        log(conn, actor, rid, "update", "listening_activity", activity_id, new.get("slug", row["slug"]), row["revision"], revision, changed)
        return activity_detail(conn, activity_id)


# ---------- options ----------
def option_out(conn, activity_id, option_id):
    snap = repo.load_listening_activity(conn, activity_id)
    o = next(o for o in snap["options"] if o["id"] == option_id)
    item = snap["items"].get(o["item_id"], {})
    return {"id": o["id"], "item_id": o["item_id"], "sort_order": o["sort_order"], "text": item.get("text"), "meaning_en": item.get("meaning_en"), "is_target": o["item_id"] == snap["item_id"]}


def create_option(db_path, actor, rid, activity_id, body):
    with connect(db_path) as conn:
        row = load_for_edit(conn, "listening_activity", activity_id, body.revision, "listening activity")
        rules.vocabulary_item(repo, conn, body.item_id, row["language_id"])
        existing = repo.options_of(conn, activity_id)
        if len(existing) >= rules.LISTENING_OPTIONS:
            raise Conflict("option_limit", f"A listening activity has exactly {rules.LISTENING_OPTIONS} options; change an existing one instead.")
        if repo.option_item_taken(conn, activity_id, body.item_id):
            raise InvalidInput("item_id", "that phrase is already an option of this activity")
        sort_order = body.sort_order if body.sort_order is not None else max([o["sort_order"] for o in existing], default=0) + 1
        if repo.option_sort_taken(conn, activity_id, sort_order):
            raise Conflict("sort_order_taken", "Another option of this activity already has that position.")
        revision = save_edit(conn, "listening_activity", activity_id, body.revision, "listening activity")
        oid = repo.insert_option(conn, activity_id, row["language_id"], body.item_id, sort_order)
        log(conn, actor, rid, "create", "listening_option", oid, row["slug"], row["revision"], revision)
        return {"revision": revision, "option": option_out(conn, activity_id, oid)}


def update_option(db_path, actor, rid, activity_id, option_id, body):
    fields = body.model_fields_set - {"revision"}
    with connect(db_path) as conn:
        row = load_for_edit(conn, "listening_activity", activity_id, body.revision, "listening activity")
        option = repo.option_row(conn, activity_id, option_id)
        if option is None:
            raise NotFound()
        new = {}
        if "item_id" in fields:
            rules.vocabulary_item(repo, conn, body.item_id, row["language_id"])
            if body.item_id != option["item_id"] and repo.option_item_taken(conn, activity_id, body.item_id, option_id):
                raise InvalidInput("item_id", "that phrase is already an option of this activity")
            new["item_id"] = body.item_id
        if "sort_order" in fields:
            if body.sort_order is None or body.sort_order < 1:
                raise InvalidInput("sort_order", "must be 1 or more")
            if body.sort_order != option["sort_order"] and repo.option_sort_taken(conn, activity_id, body.sort_order, option_id):
                raise Conflict("sort_order_taken", "Another option of this activity already has that position.")
            new["sort_order"] = body.sort_order
        changed = [("item" if k == "item_id" else k) for k, v in new.items() if option[k] != v]
        if "item_id" in new and new["item_id"] != option["item_id"]:
            if repo.option_has_attempts(conn, option_id):
                raise Conflict("option_in_use", "A learner has chosen this option, so the phrase it stands for cannot change.")
            if option["item_id"] == row["item_id"] and repo.activity_has_attempts(conn, activity_id):
                raise Conflict("activity_in_use", "This option is the correct answer of an activity learners have answered, so it cannot change.")
        if not changed:
            return {"revision": row["revision"], "option": option_out(conn, activity_id, option_id)}
        revision = save_edit(conn, "listening_activity", activity_id, body.revision, "listening activity")
        repo.update_option(conn, option_id, {k: v for k, v in new.items() if option[k] != v})
        log(conn, actor, rid, "update", "listening_option", option_id, row["slug"], row["revision"], revision, changed)
        return {"revision": revision, "option": option_out(conn, activity_id, option_id)}
