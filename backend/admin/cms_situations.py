"""The curriculum CMS, part 2: situations and their steps. Same edit protocol as lessons (see cms.py)."""
import sqlite3

from ..db import connect
from ..repositories import admin_content as repo
from . import audit, rules
from .cms import (MAX_PROMPT, MAX_PROSE, MAX_SHORT, MAX_TITLE, _constraint, _check_answer_edits, load_for_edit, log, save_edit)
from .errors import Conflict, InvalidInput, NotFound

STEP_SHAPES = {"learn_phrase": "none", "choose_response": "choose", "translate": "typed", "fill_blank": "typed", "conversation": "typed"}


def situation_detail(conn, situation_id):
    snap = repo.load_situation(conn, situation_id)
    if snap is None:
        raise NotFound()
    row = repo.unit_row(conn, "situation", situation_id)
    return {
        "id": snap["id"], "slug": snap["slug"], "language": repo.unit_languages(conn, row), "cefr": snap["cefr_code"], "title": snap["title"], "description": snap["description"],
        "goal": snap["goal"], "setting": snap["setting"], "partner_name": snap["partner_name"], "partner_role": snap["partner_role"], "difficulty": snap["difficulty"],
        "topic": snap["topic"]["slug"] if snap["topic"] else None, "sort_order": snap["sort_order"], "status": snap["status"], "revision": snap["revision"],
        "published_at": snap["published_at"], "archived_at": snap["archived_at"], "updated_at": snap["updated_at"], "age_groups": repo.age_group_codes(conn, "situation", situation_id),
        "steps": [{"id": s["id"], "sort_order": s["sort_order"], "kind": s["kind"], "prompt": s["prompt"], "prompt_meaning": s["prompt_meaning"], "item_id": s["item_id"],
                   "explanation": s["explanation"], "answers": [{"id": a["id"], "text": a["text"], "is_correct": a["is_correct"], "sort_order": a["sort_order"]} for a in s["answers"]]}
                  for s in snap["steps"]],
    }


def list_situations(db_path, status, language, cefr, q, limit, offset):
    with connect(db_path) as conn:
        language_id = None
        if language:
            lang = repo.language_by_code(conn, language)
            if lang is None:
                return 0, []
            language_id = lang["id"]
        return repo.list_units(conn, "situation", status, language_id, cefr, q, limit, offset, repo.SITUATION_COUNTS)


def get_situation(db_path, situation_id):
    with connect(db_path) as conn:
        return situation_detail(conn, situation_id)


def _topic(conn, slug):
    tid = repo.topic_id(conn, slug)
    if tid is None:
        raise InvalidInput("topic", f"Unknown topic: {slug}")
    return tid


def _partner(name, role):
    if (name is None) != (role is None):
        raise InvalidInput("partner_name", "give both the partner's name and role, or neither")


def create_situation(db_path, actor, rid, body):
    with connect(db_path) as conn:
        language_id = rules.language_id(repo, conn, body.language)
        rules.check_level(repo, conn, language_id, body.cefr)
        slug = rules.clean_slug("slug", body.slug)
        if repo.slug_taken(conn, "situation", language_id, slug):
            raise Conflict("slug_taken", "Another situation in this language already uses that slug.")
        f = {"language_id": language_id, "cefr": body.cefr, "slug": slug, "topic_id": _topic(conn, body.topic),
             "title": rules.clean_text("title", body.title, MAX_TITLE), "description": rules.clean_text("description", body.description, MAX_PROSE, multiline=True),
             "goal": rules.clean_text("goal", body.goal, MAX_SHORT, required=False, multiline=True), "setting": rules.clean_text("setting", body.setting, MAX_SHORT, required=False, multiline=True),
             "partner_name": rules.clean_text("partner_name", body.partner_name, 60, required=False), "partner_role": rules.clean_text("partner_role", body.partner_role, 60, required=False),
             "difficulty": rules.clean_difficulty("difficulty", body.difficulty, 5)}
        _partner(f["partner_name"], f["partner_role"])
        groups = rules.age_group_ids(repo, conn, body.age_groups)
        f["sort_order"] = body.sort_order if body.sort_order is not None else repo.next_sort(conn, "situation", language_id, body.cefr)
        if repo.sort_taken(conn, "situation", language_id, body.cefr, f["sort_order"]):
            raise Conflict("sort_order_taken", "Another situation at this level already has that position.")
        try:
            sid = repo.insert_situation(conn, f, rules.now())
        except sqlite3.IntegrityError as exc:
            _constraint(exc)
        repo.set_age_groups(conn, "situation", sid, groups)
        audit.record(conn, actor, "create", "situation", sid, slug, {"revision_after": 1}, request_id=rid)
        return situation_detail(conn, sid)


def update_situation(db_path, actor, rid, situation_id, body):
    fields = body.model_fields_set - {"revision"}
    with connect(db_path) as conn:
        row = load_for_edit(conn, "situation", situation_id, body.revision, "situation")
        new = {}
        if "slug" in fields:
            new["slug"] = rules.clean_slug("slug", body.slug)
            if new["slug"] != row["slug"] and repo.slug_taken(conn, "situation", row["language_id"], new["slug"], situation_id):
                raise Conflict("slug_taken", "Another situation in this language already uses that slug.")
        if "cefr" in fields:
            rules.check_level(repo, conn, row["language_id"], body.cefr)
            new["cefr_code"] = body.cefr
        if "topic" in fields:
            new["topic_id"] = _topic(conn, body.topic)
        for name, max_len, required, multiline in (("title", MAX_TITLE, True, False), ("description", MAX_PROSE, True, True), ("goal", MAX_SHORT, False, True),
                                                   ("setting", MAX_SHORT, False, True), ("partner_name", 60, False, False), ("partner_role", 60, False, False)):
            if name in fields:
                new[name] = rules.clean_text(name, getattr(body, name), max_len, required=required, multiline=multiline)
        if "difficulty" in fields:
            new["difficulty"] = rules.clean_difficulty("difficulty", body.difficulty, 5)
        if "sort_order" in fields:
            new["sort_order"] = body.sort_order
        _partner(new.get("partner_name", row["partner_name"]), new.get("partner_role", row["partner_role"]))
        cefr_after, sort_after = new.get("cefr_code", row["cefr_code"]), new.get("sort_order", row["sort_order"])
        if (cefr_after, sort_after) != (row["cefr_code"], row["sort_order"]) and repo.sort_taken(conn, "situation", row["language_id"], cefr_after, sort_after, situation_id):
            raise Conflict("sort_order_taken", "Another situation at this level already has that position.")
        groups = rules.age_group_ids(repo, conn, body.age_groups) if "age_groups" in fields else None
        names = {"cefr_code": "cefr", "topic_id": "topic"}
        changed = [names.get(k, k) for k, v in new.items() if row[k] != v]
        current_groups = sorted(r[0] for r in conn.execute("SELECT age_group_id FROM situation_age_groups WHERE situation_id = ?", (situation_id,)))
        if groups is not None and sorted(groups) != current_groups:
            changed.append("age_groups")
        if not changed:
            return situation_detail(conn, situation_id)
        revision = save_edit(conn, "situation", situation_id, body.revision, "situation")
        try:
            repo.update_fields(conn, "situation", situation_id, {k: v for k, v in new.items() if row[k] != v})
        except sqlite3.IntegrityError as exc:
            _constraint(exc)
        if "age_groups" in changed:
            repo.set_age_groups(conn, "situation", situation_id, groups)
        log(conn, actor, rid, "update", "situation", situation_id, new.get("slug", row["slug"]), row["revision"], revision, changed)
        return situation_detail(conn, situation_id)


# ---------- steps ----------
def step_out(conn, situation_id, step_id):
    s = repo.step_row(conn, situation_id, step_id)
    return {"id": s["id"], "sort_order": s["sort_order"], "kind": s["kind"], "prompt": s["prompt"], "prompt_meaning": s["prompt_meaning"], "item_id": s["item_id"], "explanation": s["explanation"],
            "answers": [{"id": a["id"], "text": a["text"], "is_correct": bool(a["is_correct"]), "sort_order": a["sort_order"]} for a in repo.step_answers(conn, step_id)]}


def create_step(db_path, actor, rid, situation_id, body):
    with connect(db_path) as conn:
        row = load_for_edit(conn, "situation", situation_id, body.revision, "situation")
        kind = body.kind
        if kind == "learn_phrase":
            if body.item_id is None:
                raise InvalidInput("item_id", "a learn-phrase step needs a vocabulary item")
        prompt = rules.clean_text("prompt", body.prompt, MAX_PROMPT, required=(kind != "learn_phrase"))
        meaning = rules.clean_text("prompt_meaning", body.prompt_meaning, MAX_SHORT, required=False, multiline=True)
        explanation = rules.clean_text("explanation", body.explanation, MAX_PROSE, required=False, multiline=True)
        if body.item_id is not None:
            rules.vocabulary_item(repo, conn, body.item_id, row["language_id"])
        if any(a.id is not None for a in body.answers):
            raise InvalidInput("answers", "new answers have no id")
        answers = rules.clean_answers("answers", body.answers, STEP_SHAPES[kind])
        sort_order = body.sort_order if body.sort_order is not None else repo.next_step_sort(conn, situation_id)
        if repo.step_sort_taken(conn, situation_id, sort_order):
            raise Conflict("sort_order_taken", "Another step in this situation already has that position.")
        revision = save_edit(conn, "situation", situation_id, body.revision, "situation")
        sid = repo.insert_step(conn, situation_id, row["language_id"], sort_order, kind, prompt, meaning, body.item_id, explanation)
        for n, a in enumerate(answers, 1):
            repo.insert_step_answer(conn, sid, a["text"], a["is_correct"], n)
        log(conn, actor, rid, "create", "situation_step", sid, row["slug"], row["revision"], revision)
        return {"revision": revision, "step": step_out(conn, situation_id, sid)}


def update_step(db_path, actor, rid, situation_id, step_id, body):
    fields = body.model_fields_set - {"revision"}
    with connect(db_path) as conn:
        row = load_for_edit(conn, "situation", situation_id, body.revision, "situation")
        step = repo.step_row(conn, situation_id, step_id)
        if step is None:
            raise NotFound()
        new = {}
        if "prompt" in fields:
            new["prompt"] = rules.clean_text("prompt", body.prompt, MAX_PROMPT, required=(step["kind"] != "learn_phrase"))
        if "prompt_meaning" in fields:
            new["prompt_meaning"] = rules.clean_text("prompt_meaning", body.prompt_meaning, MAX_SHORT, required=False, multiline=True)
        if "explanation" in fields:
            new["explanation"] = rules.clean_text("explanation", body.explanation, MAX_PROSE, required=False, multiline=True)
        if "item_id" in fields:
            if body.item_id is None and step["kind"] == "learn_phrase":
                raise InvalidInput("item_id", "a learn-phrase step needs a vocabulary item")
            if body.item_id is not None:
                rules.vocabulary_item(repo, conn, body.item_id, row["language_id"])
            new["item_id"] = body.item_id
        if "sort_order" in fields:
            if body.sort_order is None or body.sort_order < 1:
                raise InvalidInput("sort_order", "must be 1 or more")
            if body.sort_order != step["sort_order"] and repo.step_sort_taken(conn, situation_id, body.sort_order, step_id):
                raise Conflict("sort_order_taken", "Another step in this situation already has that position.")
            new["sort_order"] = body.sort_order
        if "item_id" in new and new["item_id"] != step["item_id"] and repo.step_has_attempts(conn, step_id):
            raise Conflict("step_in_use", "Learners have attempted this step, so its vocabulary item cannot change.")
        cleaned = None
        existing = repo.step_answers(conn, step_id)
        if "answers" in fields:
            cleaned = rules.clean_answers("answers", body.answers, STEP_SHAPES[step["kind"]])
            _check_answer_edits(existing, cleaned, lambda aid: repo.step_answer_used(conn, aid))
        changed = [("item" if k == "item_id" else k) for k, v in new.items() if step[k] != v]
        if cleaned is not None:
            current = [(a["id"], a["text"], bool(a["is_correct"]), a["sort_order"]) for a in existing]
            if current != [(a["id"], a["text"], a["is_correct"], n) for n, a in enumerate(cleaned, 1)]:
                changed.append("answers")
        if not changed:
            return {"revision": row["revision"], "step": step_out(conn, situation_id, step_id)}
        revision = save_edit(conn, "situation", situation_id, body.revision, "situation")
        repo.update_step(conn, step_id, {k: v for k, v in new.items() if step[k] != v})
        if "answers" in changed:
            repo.park_step_answer_orders(conn, step_id)
            for n, a in enumerate(cleaned, 1):
                if a["id"] is None:
                    repo.insert_step_answer(conn, step_id, a["text"], a["is_correct"], n)
                else:
                    repo.update_step_answer(conn, a["id"], a["text"], a["is_correct"], n)
        log(conn, actor, rid, "update", "situation_step", step_id, row["slug"], row["revision"], revision, changed)
        return {"revision": revision, "step": step_out(conn, situation_id, step_id)}
