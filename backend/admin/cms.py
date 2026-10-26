"""The curriculum CMS, part 1: the shared edit protocol and lessons (with their exercises and vocabulary links).

The protocol every edit follows (and the tests prove):
  1. only a DRAFT can be edited (published/archived content is refused with 409 not_draft: unpublish or restore first);
  2. the caller's `revision` must be the row's current revision (409 stale_revision, with current_revision, otherwise);
  3. an edit that changes nothing is not an edit: no revision bump, no audit event;
  4. a real edit bumps the revision with one guarded UPDATE, applies the change and writes the audit event, all in one transaction;
  5. nothing here deletes a row. Answers and options cannot be removed, only corrected; evidence-bearing fields are locked once learners have used them."""
import sqlite3

from ..db import connect
from ..repositories import admin_content as repo
from ..textnorm import normalize
from . import audit, rules
from .errors import Conflict, InvalidInput, NotFound

MAX_TITLE, MAX_PROSE, MAX_SHORT, MAX_PROMPT = 120, 2000, 500, 500
EXERCISE_KINDS = {"multiple_choice": "choose", "translation": "typed", "fill_blank": "typed"}


# ---------- the shared protocol ----------
def load_for_edit(conn, entity_type, entity_id, expected_revision, what):
    row = repo.unit_row(conn, entity_type, entity_id)
    if row is None:
        raise NotFound()
    rules.ensure_draft(row, what)
    if row["revision"] != expected_revision:
        raise Conflict("stale_revision", f"This {what} changed since you opened it (it is now revision {row['revision']}). Reload and try again.", current_revision=row["revision"])
    return row


def save_edit(conn, entity_type, entity_id, expected_revision, what):
    new = repo.bump(conn, entity_type, entity_id, expected_revision, rules.now())
    if new is None:
        raise Conflict("stale_revision", f"This {what} was changed by someone else a moment ago. Reload and try again.")
    return new


def log(conn, actor, rid, action, entity_type, entity_id, key, before, after, fields=None):
    meta = {"revision_before": before, "revision_after": after}
    if fields:
        meta["changed_fields"] = fields
    audit.record(conn, actor, action, entity_type, entity_id, key, meta, request_id=rid)


def _constraint(exc):
    """A UNIQUE race that slipped past the pre-checks becomes the same 409 the pre-check would have produced."""
    raise Conflict("conflict", "That value is already taken.") from exc


# ---------- lessons: reads ----------
def lesson_detail(conn, lesson_id):
    snap = repo.load_lesson(conn, lesson_id)
    if snap is None:
        raise NotFound()
    row = repo.unit_row(conn, "lesson", lesson_id)
    names = {r["slug"]: r["name"] for r in conn.execute("SELECT slug, name FROM topics")}
    return {
        "id": snap["id"], "slug": snap["slug"], "language": repo.unit_languages(conn, row), "cefr": snap["cefr_code"], "title": snap["title"],
        "description": snap["description"], "situation": snap["situation"], "tip": snap["tip"], "sort_order": snap["sort_order"], "status": snap["status"],
        "revision": snap["revision"], "published_at": snap["published_at"], "archived_at": snap["archived_at"], "updated_at": snap["updated_at"],
        "topics": [{"slug": t["slug"], "name": names[t["slug"]]} for t in snap["topics"]], "age_groups": repo.age_group_codes(conn, "lesson", lesson_id),
        "vocabulary": [{"item_id": i, "text": snap["items"][i]["text"], "meaning_en": snap["items"][i]["meaning_en"], "sort_order": n}
                       for n, i in enumerate(snap["vocabulary_ids"], 1) if i in snap["items"]],
        "exercises": [{"id": e["id"], "kind": e["kind"], "prompt": e["prompt"], "explanation": e["explanation"], "item_id": e["item_id"], "difficulty": e["difficulty"],
                       "sort_order": e["sort_order"], "answers": [{"id": a["id"], "text": a["text"], "is_correct": a["is_correct"], "sort_order": a["sort_order"]} for a in e["answers"]]}
                      for e in snap["exercises"]],
    }


def list_lessons(db_path, status, language, cefr, q, limit, offset):
    with connect(db_path) as conn:
        language_id = None
        if language:
            lang = repo.language_by_code(conn, language)
            if lang is None:
                return 0, []
            language_id = lang["id"]
        return repo.list_units(conn, "lesson", status, language_id, cefr, q, limit, offset, repo.LESSON_COUNTS)


def get_lesson(db_path, lesson_id):
    with connect(db_path) as conn:
        return lesson_detail(conn, lesson_id)


# ---------- lessons: writes ----------
def _lesson_text(body_fields, get):
    out = {}
    if "title" in body_fields:
        out["title"] = rules.clean_text("title", get("title"), MAX_TITLE)
    if "description" in body_fields:
        out["description"] = rules.clean_text("description", get("description"), MAX_PROSE, multiline=True)
    if "situation" in body_fields:
        out["situation"] = rules.clean_text("situation", get("situation"), MAX_SHORT, required=False, multiline=True)
    if "tip" in body_fields:
        out["tip"] = rules.clean_text("tip", get("tip"), MAX_SHORT, required=False, multiline=True)
    return out


def create_lesson(db_path, actor, rid, body):
    fields = body.model_fields_set
    with connect(db_path) as conn:
        language_id = rules.language_id(repo, conn, body.language)
        cefr = body.cefr
        rules.check_level(repo, conn, language_id, cefr)
        slug = rules.clean_slug("slug", body.slug)
        if repo.slug_taken(conn, "lesson", language_id, slug):
            raise Conflict("slug_taken", "Another lesson in this language already uses that slug.")
        text = _lesson_text({"title", "description", "situation", "tip"} | (fields & {"situation", "tip"}), lambda f: getattr(body, f))
        topics = rules.topic_ids(repo, conn, body.topics)
        groups = rules.age_group_ids(repo, conn, body.age_groups)
        sort_order = body.sort_order if body.sort_order is not None else repo.next_sort(conn, "lesson", language_id, cefr)
        if repo.sort_taken(conn, "lesson", language_id, cefr, sort_order):
            raise Conflict("sort_order_taken", "Another lesson at this level already has that position.")
        try:
            lid = repo.insert_lesson(conn, language_id, cefr, slug, text["title"], text["description"], text.get("situation"), text.get("tip"), sort_order, rules.now())
        except sqlite3.IntegrityError as exc:
            _constraint(exc)
        repo.set_lesson_topics(conn, lid, topics)
        repo.set_age_groups(conn, "lesson", lid, groups)
        audit.record(conn, actor, "create", "lesson", lid, slug, {"revision_after": 1}, request_id=rid)
        return lesson_detail(conn, lid)


def update_lesson(db_path, actor, rid, lesson_id, body):
    fields = body.model_fields_set - {"revision"}
    with connect(db_path) as conn:
        row = load_for_edit(conn, "lesson", lesson_id, body.revision, "lesson")
        new = {}
        if "slug" in fields:
            new["slug"] = rules.clean_slug("slug", body.slug)
            if new["slug"] != row["slug"] and repo.slug_taken(conn, "lesson", row["language_id"], new["slug"], lesson_id):
                raise Conflict("slug_taken", "Another lesson in this language already uses that slug.")
        if "cefr" in fields:
            new["cefr_code"] = body.cefr
            rules.check_level(repo, conn, row["language_id"], body.cefr)
        new.update(_lesson_text(fields, lambda f: getattr(body, f)))
        if "sort_order" in fields:
            new["sort_order"] = body.sort_order
        cefr_after, sort_after = new.get("cefr_code", row["cefr_code"]), new.get("sort_order", row["sort_order"])
        if (cefr_after, sort_after) != (row["cefr_code"], row["sort_order"]) and repo.sort_taken(conn, "lesson", row["language_id"], cefr_after, sort_after, lesson_id):
            raise Conflict("sort_order_taken", "Another lesson at this level already has that position.")
        topics = rules.topic_ids(repo, conn, body.topics) if "topics" in fields else None
        groups = rules.age_group_ids(repo, conn, body.age_groups) if "age_groups" in fields else None

        names = {"cefr_code": "cefr"}
        changed = [names.get(k, k) for k, v in new.items() if row[k] != v]
        current_topics = sorted(r[0] for r in conn.execute("SELECT topic_id FROM lesson_topics WHERE lesson_id = ?", (lesson_id,)))
        if topics is not None and sorted(topics) != current_topics:
            changed.append("topics")
        current_groups = sorted(r[0] for r in conn.execute("SELECT age_group_id FROM lesson_age_groups WHERE lesson_id = ?", (lesson_id,)))
        if groups is not None and sorted(groups) != current_groups:
            changed.append("age_groups")
        if not changed:
            return lesson_detail(conn, lesson_id)
        revision = save_edit(conn, "lesson", lesson_id, body.revision, "lesson")
        try:
            repo.update_fields(conn, "lesson", lesson_id, {k: v for k, v in new.items() if row[k] != v})
        except sqlite3.IntegrityError as exc:
            _constraint(exc)
        if "topics" in changed:
            repo.set_lesson_topics(conn, lesson_id, topics)
        if "age_groups" in changed:
            repo.set_age_groups(conn, "lesson", lesson_id, groups)
        log(conn, actor, rid, "update", "lesson", lesson_id, new.get("slug", row["slug"]), row["revision"], revision, changed)
        return lesson_detail(conn, lesson_id)


# ---------- exercises ----------
def exercise_out(conn, lesson_id, exercise_id):
    e = repo.exercise_row(conn, lesson_id, exercise_id)
    return {"id": e["id"], "kind": e["kind"], "prompt": e["prompt"], "explanation": e["explanation"], "item_id": e["item_id"], "difficulty": e["difficulty"],
            "sort_order": e["sort_order"], "answers": [{"id": a["id"], "text": a["text"], "is_correct": bool(a["is_correct"]), "sort_order": a["sort_order"]} for a in repo.exercise_answers(conn, exercise_id)]}


def create_exercise(db_path, actor, rid, lesson_id, body):
    with connect(db_path) as conn:
        row = load_for_edit(conn, "lesson", lesson_id, body.revision, "lesson")
        prompt = rules.clean_text("prompt", body.prompt, MAX_PROMPT)
        explanation = rules.clean_text("explanation", body.explanation, MAX_PROSE, required=False, multiline=True)
        if body.item_id is not None:
            rules.vocabulary_item(repo, conn, body.item_id, row["language_id"])
        difficulty = rules.clean_difficulty("difficulty", body.difficulty, 3)
        if any(a.id is not None for a in body.answers):
            raise InvalidInput("answers", "new answers have no id")
        answers = rules.clean_answers("answers", body.answers, EXERCISE_KINDS[body.kind])
        sort_order = body.sort_order if body.sort_order is not None else repo.next_exercise_sort(conn, lesson_id)
        if repo.exercise_sort_taken(conn, lesson_id, sort_order):
            raise Conflict("sort_order_taken", "Another exercise in this lesson already has that position.")
        revision = save_edit(conn, "lesson", lesson_id, body.revision, "lesson")
        eid = repo.insert_exercise(conn, lesson_id, row["language_id"], body.kind, prompt, explanation, body.item_id, sort_order, difficulty)
        for n, a in enumerate(answers, 1):
            repo.insert_exercise_answer(conn, eid, a["text"], a["is_correct"], n)
        log(conn, actor, rid, "create", "exercise", eid, row["slug"], row["revision"], revision)
        return {"revision": revision, "exercise": exercise_out(conn, lesson_id, eid)}


def _check_answer_edits(existing, cleaned, used):
    """existing: current rows; cleaned: the full new list. Existing answers may be corrected, never removed; a learner-chosen answer keeps its
    correctness and may only have typo-level text changes."""
    by_id = {a["id"]: a for a in existing}
    given = {a["id"] for a in cleaned if a["id"] is not None}
    if given - set(by_id):
        raise InvalidInput("answers", "unknown answer id")
    if set(by_id) - given:
        raise InvalidInput("answers", "existing answers cannot be removed, only corrected")
    for a in cleaned:
        if a["id"] is None:
            continue
        old = by_id[a["id"]]
        if used(a["id"]):
            if bool(old["is_correct"]) != a["is_correct"]:
                raise Conflict("answer_in_use", "A learner has already chosen this answer, so whether it is correct cannot change.")
            if normalize(old["text"]) != normalize(a["text"]):
                raise Conflict("answer_in_use", "A learner has already chosen this answer, so only a typo-level change (case or punctuation) is allowed.")


def update_exercise(db_path, actor, rid, lesson_id, exercise_id, body):
    fields = body.model_fields_set - {"revision"}
    with connect(db_path) as conn:
        row = load_for_edit(conn, "lesson", lesson_id, body.revision, "lesson")
        ex = repo.exercise_row(conn, lesson_id, exercise_id)
        if ex is None:
            raise NotFound()
        new = {}
        if "prompt" in fields:
            new["prompt"] = rules.clean_text("prompt", body.prompt, MAX_PROMPT)
        if "explanation" in fields:
            new["explanation"] = rules.clean_text("explanation", body.explanation, MAX_PROSE, required=False, multiline=True)
        if "item_id" in fields:
            if body.item_id is not None:
                rules.vocabulary_item(repo, conn, body.item_id, row["language_id"])
            new["item_id"] = body.item_id
        if "difficulty" in fields:
            new["difficulty"] = rules.clean_difficulty("difficulty", body.difficulty, 3)
        if "sort_order" in fields:
            if body.sort_order is None or body.sort_order < 1:
                raise InvalidInput("sort_order", "must be 1 or more")
            if body.sort_order != ex["sort_order"] and repo.exercise_sort_taken(conn, lesson_id, body.sort_order, exercise_id):
                raise Conflict("sort_order_taken", "Another exercise in this lesson already has that position.")
            new["sort_order"] = body.sort_order
        has_attempts = repo.exercise_has_attempts(conn, exercise_id)
        locked = [k for k in ("item_id", "difficulty") if k in new and new[k] != ex[k]]
        if locked and has_attempts:
            raise Conflict("exercise_in_use", f"Learners have attempted this exercise, so its {locked[0].replace('_id', '')} cannot change.")
        cleaned = None
        existing = repo.exercise_answers(conn, exercise_id)
        if "answers" in fields:
            cleaned = rules.clean_answers("answers", body.answers, EXERCISE_KINDS[ex["kind"]])
            _check_answer_edits(existing, cleaned, lambda aid: repo.exercise_answer_used(conn, aid))
        changed = [("item" if k == "item_id" else k) for k, v in new.items() if ex[k] != v]
        if cleaned is not None:
            current = [(a["id"], a["text"], bool(a["is_correct"]), a["sort_order"]) for a in existing]
            proposed = [(a["id"], a["text"], a["is_correct"], n) for n, a in enumerate(cleaned, 1)]
            if current != proposed:
                changed.append("answers")
        if not changed:
            return {"revision": row["revision"], "exercise": exercise_out(conn, lesson_id, exercise_id)}
        revision = save_edit(conn, "lesson", lesson_id, body.revision, "lesson")
        repo.update_exercise(conn, exercise_id, {k: v for k, v in new.items() if ex[k] != v})
        if "answers" in changed:
            repo.park_exercise_answer_orders(conn, exercise_id)
            for n, a in enumerate(cleaned, 1):
                if a["id"] is None:
                    repo.insert_exercise_answer(conn, exercise_id, a["text"], a["is_correct"], n)
                else:
                    repo.update_exercise_answer(conn, a["id"], a["text"], a["is_correct"], n)
        log(conn, actor, rid, "update", "exercise", exercise_id, row["slug"], row["revision"], revision, changed)
        return {"revision": revision, "exercise": exercise_out(conn, lesson_id, exercise_id)}


def set_lesson_vocabulary(db_path, actor, rid, lesson_id, body):
    with connect(db_path) as conn:
        row = load_for_edit(conn, "lesson", lesson_id, body.revision, "lesson")
        if len(set(body.item_ids)) != len(body.item_ids):
            raise InvalidInput("item_ids", "the same vocabulary item is listed more than once")
        for item_id in body.item_ids:
            rules.vocabulary_item(repo, conn, item_id, row["language_id"], "item_ids")
        if repo.lesson_vocabulary_ids(conn, lesson_id) == body.item_ids:
            return lesson_detail(conn, lesson_id)
        revision = save_edit(conn, "lesson", lesson_id, body.revision, "lesson")
        repo.set_lesson_vocabulary(conn, lesson_id, row["language_id"], body.item_ids)
        log(conn, actor, rid, "update", "lesson_vocabulary", lesson_id, row["slug"], row["revision"], revision, ["vocabulary"])
        return lesson_detail(conn, lesson_id)
