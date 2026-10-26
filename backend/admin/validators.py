"""The content validators: pure functions over a snapshot (backend/repositories/admin_content.py), no database access, no side effects.

The SAME functions power the dry run (POST /validate/...), the publish gate and the integrity sweep (GET /validate/all), so the three can never
disagree: they differ only in what they do with the findings. A finding is {code, severity, entity, message}; the severity comes from the single
catalogue in codes.py ('error' blocks publication, 'warning' does not). Messages describe the problem and never quote answer text."""
import re
import unicodedata
from collections import Counter

from .. import settings
from ..textnorm import normalize
from .codes import FINDING_CODES

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG = 60
TYPED_EXERCISES = ("translation", "fill_blank")
TYPED_STEPS = ("translate", "fill_blank", "conversation")


def finding(code, entity, message):
    return {"code": code, "severity": FINDING_CODES[code], "entity": entity, "message": message}


def has_control_characters(text, multiline=False):
    """A control character (category Cc) anywhere in the text. A newline is allowed in the fields that are multi-line prose."""
    return any(unicodedata.category(ch) == "Cc" and not (multiline and ch == "\n") for ch in text or "")


def _text_findings(entity, fields, out):
    """fields: [(label, value, multiline)]"""
    for label, value, multiline in fields:
        if isinstance(value, str) and has_control_characters(value, multiline):
            out.append(finding("text_control_characters", entity, f"{label} contains a control character."))


def _shared(snap, entity, out):
    if not isinstance(snap["slug"], str) or len(snap["slug"]) > MAX_SLUG or not SLUG.match(snap["slug"]):
        out.append(finding("slug_invalid", entity, "The slug must be lowercase letters and digits separated by single hyphens (60 characters at most)."))
    if not snap["level_valid"]:
        out.append(finding("language_level_invalid", entity, "This language does not offer this CEFR level."))
    seen = Counter(snap["age_group_ids"])
    for gid in sorted(seen):
        if gid not in snap["known_age_group_ids"]:
            out.append(finding("age_group_unknown", entity, "The age targeting names an age group that does not exist."))
        if seen[gid] > 1:
            out.append(finding("age_group_duplicate", entity, "The same age group is targeted more than once."))
    # a lesson with no age rows is open to every age group (empty targeting means universal); that is valid
    for dep in snap["dependencies"]:
        if dep["status"] is not None and dep["status"] != "published":
            out.append(finding("dependency_unpublished", entity, f"It depends on a {dep['type']} that is {dep['status']}."))
    if snap["status"] == "archived" and not snap["archived_at"]:
        out.append(finding("lifecycle_archived_without_time", entity, "It is archived but has no archive time."))
    if snap["status"] != "archived" and snap["archived_at"]:
        out.append(finding("lifecycle_time_without_archive", entity, "It has an archive time but is not archived."))
    if snap["status"] == "published" and not snap["published_at"]:
        out.append(finding("lifecycle_published_without_time", entity, "It is published but has no publish time."))


def _items(snap, entity, used_ids, out):
    """Every vocabulary item the content uses: it exists, has an English translation and is not above the content's CEFR level."""
    for item_id in sorted({i for i in used_ids if i is not None}):
        item = snap["items"].get(item_id)
        if item is None:
            out.append(finding("vocabulary_unknown", entity, "It uses a vocabulary item that does not exist."))
            continue
        if not item["meaning_en"] or not item["meaning_en"].strip():
            out.append(finding("vocabulary_missing_english", entity, f"Vocabulary item {item_id} has no English translation."))
        if snap["cefr_rank"] is not None and item["cefr_rank"] > snap["cefr_rank"]:
            out.append(finding("vocabulary_cefr_above_unit", entity, f"Vocabulary item {item_id} is above this content's CEFR level."))


def _duplicates(texts):
    counts = Counter(normalize(t) for t in texts)
    return any(n > 1 for n in counts.values())


# ---------- lessons ----------
def validate_lesson(snap):
    entity = f"lesson:{snap['id']}"
    out = []
    _shared(snap, entity, out)
    _text_findings(entity, [("The title", snap["title"], False), ("The description", snap["description"], True), ("The situation", snap["situation"], True),
                            ("The tip", snap["tip"], True)], out)
    if not snap["exercises"]:
        out.append(finding("lesson_no_exercises", entity, "A lesson needs at least one exercise."))
    if not snap["topics"]:
        out.append(finding("lesson_no_topics", entity, "A lesson needs at least one topic."))
    if not snap["vocabulary_ids"]:
        out.append(finding("lesson_no_vocabulary", entity, "A lesson needs at least one vocabulary item."))
    if snap["sibling_title_count"]:
        out.append(finding("lesson_duplicate_title", entity, "Another lesson has the same title for this language and level."))
    if _duplicates(e["prompt"] for e in snap["exercises"]):
        out.append(finding("exercise_duplicate_prompt", entity, "Two exercises in this lesson have the same prompt."))
    linked = set(snap["vocabulary_ids"])
    for e in snap["exercises"]:
        _exercise(snap, e, linked, out)
    _items(snap, entity, [*snap["vocabulary_ids"], *[e["item_id"] for e in snap["exercises"]]], out)
    return out


def _exercise(snap, e, linked, out):
    entity = f"exercise:{e['id']}"
    answers = e["answers"]
    _text_findings(entity, [("The prompt", e["prompt"], False), ("The explanation", e["explanation"], True)] + [("An answer", a["text"], False) for a in answers], out)
    if not 1 <= e["difficulty"] <= 3:
        out.append(finding("exercise_invalid_difficulty", entity, "Exercise difficulty must be 1, 2 or 3."))
    correct = sum(1 for a in answers if a["is_correct"])
    if e["kind"] == "multiple_choice":
        if len(answers) < 2:
            out.append(finding("exercise_mc_too_few_answers", entity, "A multiple-choice exercise needs at least two answers."))
        if correct != 1:
            out.append(finding("exercise_mc_correct_count", entity, f"A multiple-choice exercise needs exactly one correct answer (it has {correct})."))
    elif e["kind"] in TYPED_EXERCISES:
        if correct < 1:
            out.append(finding("exercise_typed_no_accepted_answer", entity, "A typed exercise needs at least one accepted answer."))
        if correct != len(answers):
            out.append(finding("exercise_typed_incorrect_row", entity, "A typed exercise lists only accepted answers; one is marked incorrect."))
    if _duplicates(a["text"] for a in answers):
        out.append(finding("exercise_duplicate_answers", entity, "Two answers of this exercise are the same once case and punctuation are ignored."))
    if e["item_id"] is None:
        out.append(finding("exercise_item_missing", entity, "This exercise does not point at a canonical vocabulary item."))
    elif e["item_id"] not in linked:
        out.append(finding("exercise_item_not_in_lesson", entity, "This exercise's vocabulary item is not one of the lesson's vocabulary."))


# ---------- situations ----------
def validate_situation(snap):
    entity = f"situation:{snap['id']}"
    out = []
    _shared(snap, entity, out)
    _text_findings(entity, [("The title", snap["title"], False), ("The description", snap["description"], True), ("The goal", snap["goal"], True),
                            ("The setting", snap["setting"], True), ("The partner name", snap["partner_name"], False), ("The partner role", snap["partner_role"], False)], out)
    if snap["topic"] is None:
        out.append(finding("situation_topic_missing", entity, "The situation's topic does not exist."))
    if not 1 <= snap["difficulty"] <= 5:
        out.append(finding("situation_invalid_difficulty", entity, "Situation difficulty must be between 1 and 5."))
    if not snap["steps"]:
        out.append(finding("situation_no_steps", entity, "A situation needs at least one step."))
    if snap["sibling_title_count"]:
        out.append(finding("situation_duplicate_title", entity, "Another situation has the same title for this language and level."))
    for step in snap["steps"]:
        _step(step, out)
    _items(snap, entity, [s["item_id"] for s in snap["steps"]], out)
    return out


def _step(step, out):
    entity = f"situation_step:{step['id']}"
    answers = step["answers"]
    _text_findings(entity, [("The prompt", step["prompt"], False), ("The meaning", step["prompt_meaning"], True), ("The explanation", step["explanation"], True)]
                   + [("An answer", a["text"], False) for a in answers], out)
    correct = sum(1 for a in answers if a["is_correct"])
    if step["kind"] == "choose_response":
        if len(answers) < 2:
            out.append(finding("step_choose_too_few_answers", entity, "A choose-response step needs at least two answers."))
        if correct != 1:
            out.append(finding("step_choose_correct_count", entity, f"A choose-response step needs exactly one correct answer (it has {correct})."))
    elif step["kind"] in TYPED_STEPS:
        if correct < 1:
            out.append(finding("step_typed_no_accepted_answer", entity, "This step needs at least one accepted answer."))
        if correct != len(answers):
            out.append(finding("step_typed_incorrect_row", entity, "This step lists only accepted answers; one is marked incorrect."))
    if _duplicates(a["text"] for a in answers):
        out.append(finding("step_duplicate_answers", entity, "Two answers of this step are the same once case and punctuation are ignored."))


# ---------- listening ----------
def option_label(snap, item_id):
    """What the learner reads for an option: the phrase itself, or its English meaning when the activity asks for the meaning."""
    item = snap["items"].get(item_id)
    if item is None:
        return None
    return item["meaning_en"] if snap["mode"] == "choose_meaning" else item["text"]


def validate_listening_activity(snap):
    entity = f"listening_activity:{snap['id']}"
    out = []
    _shared(snap, entity, out)
    _text_findings(entity, [("The title", snap["title"], False), ("The prompt", snap["prompt"], True)], out)
    if snap["topic"] is None:
        out.append(finding("listening_topic_missing", entity, "The activity's topic does not exist."))
    if not 1 <= snap["difficulty"] <= 3:
        out.append(finding("listening_invalid_difficulty", entity, "Listening difficulty must be 1, 2 or 3."))
    if snap["sibling_title_count"]:
        out.append(finding("listening_duplicate_title", entity, "Another listening activity has the same title for this language and level."))
    option_items = [o["item_id"] for o in snap["options"]]
    if len(option_items) != settings.LISTENING_OPTION_COUNT:
        out.append(finding("listening_option_count", entity, f"A listening activity offers exactly {settings.LISTENING_OPTION_COUNT} options (it has {len(option_items)})."))
    if snap["item_id"] not in option_items:
        out.append(finding("listening_target_not_in_options", entity, "The phrase to listen for is not one of the options."))
    labels = [option_label(snap, i) for i in option_items]
    if _duplicates([l for l in labels if l]):
        out.append(finding("listening_duplicate_option_text", entity, "Two options read the same to the learner."))
    _items(snap, entity, [snap["item_id"], *option_items], out)
    return out


VALIDATORS = {"lesson": validate_lesson, "situation": validate_situation, "listening_activity": validate_listening_activity}


def errors(findings):
    return [f for f in findings if f["severity"] == "error"]
