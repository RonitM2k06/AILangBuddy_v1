"""The curriculum CMS, part 4: vocabulary, vocabulary translations, topics and the read-only reference data.

Vocabulary is shared, canonical content: lessons, steps, activities, speaking, AI drills and learner weaknesses all point at the same row. So:
  * a language never changes;
  * while anything refers to an item, its CEFR level and kind are locked, and its text may only change in a way the answer graders ignore
    (case, punctuation, spacing: textnorm.normalize-equal) -- a typo fix, not a change of meaning;
  * its pronunciation guide may always be corrected;
  * a translation can always be ADDED; an existing translation is edited only while no published content uses the item.
Nothing here deletes anything."""
import sqlite3

from ..db import connect
from ..repositories import admin_content as repo
from ..textnorm import normalize
from . import audit, rules
from .errors import Conflict, InvalidInput, NotFound

MAX_VOCAB, MAX_MEANING = 200, 300


def vocabulary_detail(conn, item_id):
    item = repo.vocabulary_row(conn, item_id)
    if item is None:
        raise NotFound()
    lang = conn.execute("SELECT code FROM languages WHERE id = ?", (item["language_id"],)).fetchone()["code"]
    return {"id": item["id"], "language": lang, "cefr": item["cefr_code"], "kind": item["kind"], "text": item["text"], "pronunciation": item["pronunciation"],
            "translations": repo.translations_of(conn, item_id), "usage": repo.vocabulary_usage(conn, item_id), "referenced": repo.vocabulary_is_referenced(conn, item_id),
            "used_by_published": repo.vocabulary_used_by_published(conn, item_id)}


def list_vocabulary(db_path, language, cefr, kind, q, limit, offset):
    with connect(db_path) as conn:
        language_id = None
        if language:
            lang = repo.language_by_code(conn, language)
            if lang is None:
                return 0, []
            language_id = lang["id"]
        return repo.list_vocabulary(conn, language_id, cefr, kind, q, limit, offset)


def get_vocabulary(db_path, item_id):
    with connect(db_path) as conn:
        return vocabulary_detail(conn, item_id)


def _translation(conn, item_id, item_language_id, code, meaning, natural, actor, rid, creating_with_item=False):
    lang = repo.language_by_code(conn, code)
    if lang is None:
        raise InvalidInput("language", "Unknown language")
    if lang["id"] == item_language_id:
        raise InvalidInput("language", "a translation is written in a different language than the item")
    meaning = rules.clean_text("meaning", meaning, MAX_MEANING)
    natural = rules.clean_text("natural", natural, MAX_MEANING, required=False)
    old = repo.translation_row(conn, item_id, lang["id"])
    if old == {"meaning": meaning, "natural": natural}:
        return False
    if old is not None and repo.vocabulary_used_by_published(conn, item_id):
        raise Conflict("referenced_by_published", "Published content uses this item: unpublish it before changing an existing translation (adding a new language is always allowed).")
    repo.upsert_translation(conn, item_id, lang["id"], meaning, natural)
    changed = None if old is None else [k for k, v in (("meaning", meaning), ("natural", natural)) if old[k] != v]
    audit.record(conn, actor, "create" if old is None else "update", "vocabulary_translation", item_id, code, {"changed_fields": changed} if changed else None, request_id=rid)
    return True


def create_vocabulary(db_path, actor, rid, body):
    with connect(db_path) as conn:
        language_id = rules.language_id(repo, conn, body.language)
        rules.check_level(repo, conn, language_id, body.cefr)
        text = rules.clean_text("text", body.text, MAX_VOCAB)
        pronunciation = rules.clean_text("pronunciation", body.pronunciation, MAX_VOCAB, required=False)
        if repo.vocabulary_text_taken(conn, language_id, text):
            raise Conflict("text_taken", "This language already has a vocabulary item with exactly that text.")
        codes = [t.language for t in body.translations]
        if len(set(codes)) != len(codes):
            raise InvalidInput("translations", "a language is listed more than once")
        try:
            item_id = repo.insert_vocabulary(conn, language_id, body.cefr, body.kind, text, pronunciation)
        except sqlite3.IntegrityError as exc:
            raise Conflict("conflict", "That value is already taken.") from exc
        audit.record(conn, actor, "create", "vocabulary", item_id, None, request_id=rid)
        for t in body.translations:
            _translation(conn, item_id, language_id, t.language, t.meaning, t.natural, actor, rid)
        return vocabulary_detail(conn, item_id)


def update_vocabulary(db_path, actor, rid, item_id, body):
    fields = body.model_fields_set
    with connect(db_path) as conn:
        item = repo.vocabulary_row(conn, item_id)
        if item is None:
            raise NotFound()
        referenced = repo.vocabulary_is_referenced(conn, item_id)
        new = {}
        if "cefr" in fields:
            rules.check_level(repo, conn, item["language_id"], body.cefr)
            new["cefr_code"] = body.cefr
        if "kind" in fields:
            new["kind"] = body.kind
        if "text" in fields:
            new["text"] = rules.clean_text("text", body.text, MAX_VOCAB)
        if "pronunciation" in fields:
            new["pronunciation"] = rules.clean_text("pronunciation", body.pronunciation, MAX_VOCAB, required=False)
        for k in ("cefr_code", "kind"):
            if k in new and new[k] != item[k] and referenced:
                raise Conflict("vocabulary_in_use", f"Content or learner evidence uses this item, so its {'CEFR level' if k == 'cefr_code' else 'kind'} cannot change.")
        if "text" in new and new["text"] != item["text"]:
            if referenced and normalize(new["text"]) != normalize(item["text"]):
                raise Conflict("vocabulary_in_use", "Content or learner evidence uses this item: only a change of case, punctuation or spacing is allowed.")
            if repo.vocabulary_text_taken(conn, item["language_id"], new["text"], item_id):
                raise Conflict("text_taken", "This language already has a vocabulary item with exactly that text.")
        names = {"cefr_code": "cefr"}
        changed = [names.get(k, k) for k, v in new.items() if item[k] != v]
        if not changed:
            return vocabulary_detail(conn, item_id)
        try:
            repo.update_vocabulary(conn, item_id, {k: v for k, v in new.items() if item[k] != v})
        except sqlite3.IntegrityError as exc:
            raise Conflict("conflict", "That value is already taken.") from exc
        audit.record(conn, actor, "update", "vocabulary", item_id, None, {"changed_fields": changed}, request_id=rid)
        return vocabulary_detail(conn, item_id)


def put_translation(db_path, actor, rid, item_id, language_code, body):
    with connect(db_path) as conn:
        item = repo.vocabulary_row(conn, item_id)
        if item is None:
            raise NotFound()
        _translation(conn, item_id, item["language_id"], language_code, body.meaning, body.natural, actor, rid)
        return vocabulary_detail(conn, item_id)


# ---------- topics ----------
def topic_out(conn, topic_id):
    return next(t for t in repo.list_topics(conn) if t["id"] == topic_id)


def list_topics(db_path):
    with connect(db_path) as conn:
        return repo.list_topics(conn)


def create_topic(db_path, actor, rid, body):
    with connect(db_path) as conn:
        slug = rules.clean_slug("slug", body.slug)
        if repo.topic_id(conn, slug) is not None:
            raise Conflict("slug_taken", "A topic with that slug already exists.")
        name = rules.clean_text("name", body.name, 60)
        icon = rules.clean_text("icon", body.icon, 16)
        tid = repo.insert_topic(conn, slug, name, icon)
        audit.record(conn, actor, "create", "topic", tid, slug, request_id=rid)
        return topic_out(conn, tid)


def update_topic(db_path, actor, rid, topic_id, body):
    fields = body.model_fields_set
    with connect(db_path) as conn:
        row = repo.topic_row(conn, topic_id)
        if row is None:
            raise NotFound()
        name = rules.clean_text("name", body.name, 60) if "name" in fields else row["name"]
        icon = rules.clean_text("icon", body.icon, 16) if "icon" in fields else row["icon"]
        changed = [k for k, v in (("name", name), ("icon", icon)) if row[k] != v]
        if changed:
            repo.update_topic(conn, topic_id, name, icon)
            audit.record(conn, actor, "update", "topic", topic_id, row["slug"], {"changed_fields": changed}, request_id=rid)
        return topic_out(conn, topic_id)


# ---------- reference data: read-only ----------
def reference(db_path):
    with connect(db_path) as conn:
        return {"languages": repo.reference_languages(conn), "cefr_levels": repo.reference_cefr(conn), "age_groups": repo.reference_age_groups(conn)}
