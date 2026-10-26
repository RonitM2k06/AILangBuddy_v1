"""Phase 13C: the pure content validators. Each rule is driven by a minimal snapshot that breaks exactly that rule, and asserted by the exact set of
finding codes (and severities) it yields; a boundary case that must stay clean sits next to every rule."""
import copy

import pytest

from backend.admin import codes, validators
from backend.admin.validators import validate_lesson, validate_listening_activity, validate_situation


def item(i, rank=1, en="meaning"):
    return {"id": i, "language_id": 10, "text": f"word{i}", "cefr_rank": rank, "meaning_en": en if en is None else f"{en}{i}"}


def mc(i, item_id=1, answers=("a", "b", "c"), correct=0, difficulty=1):
    return {"id": i, "kind": "multiple_choice", "prompt": f"Prompt {i}", "explanation": "e", "item_id": item_id, "sort_order": i, "difficulty": difficulty,
            "answers": [{"id": i * 10 + n, "text": t, "is_correct": n == correct, "sort_order": n + 1} for n, t in enumerate(answers)]}


def typed(i, item_id=2, accepted=("one",), kind="translation"):
    return {"id": i, "kind": kind, "prompt": f"Prompt {i}", "explanation": None, "item_id": item_id, "sort_order": i, "difficulty": 1,
            "answers": [{"id": i * 10 + n, "text": t, "is_correct": True, "sort_order": n + 1} for n, t in enumerate(accepted)]}


def base(kind, **over):
    snap = {"type": kind, "id": 1, "slug": "my-unit", "title": "Title", "language_id": 10, "cefr_code": "A1", "cefr_rank": 1, "sort_order": 1, "status": "draft",
            "published_at": None, "archived_at": None, "updated_at": "2026-01-01 00:00:00", "revision": 1, "level_valid": True, "age_group_ids": [],
            "known_age_group_ids": {1, 2, 3}, "sibling_title_count": 0, "dependencies": []}
    snap.update(over)
    return snap


def lesson(**over):
    return base("lesson", **{"description": "d", "situation": "s", "tip": "t", "topics": [{"id": 1, "slug": "food"}], "vocabulary_ids": [1, 2],
                             "items": {1: item(1), 2: item(2)}, "exercises": [mc(1, 1), typed(2, 2)], **over})


def step(i, kind="choose_response", answers=("hello", "bye"), correct=0, item_id=None):
    if kind == "learn_phrase":
        return {"id": i, "sort_order": i, "kind": kind, "prompt": None, "prompt_meaning": None, "item_id": item_id or 1, "explanation": None, "answers": []}
    rows = [{"id": i * 10 + n, "text": t, "is_correct": (n == correct) if kind == "choose_response" else True, "sort_order": n + 1} for n, t in enumerate(answers)]
    return {"id": i, "sort_order": i, "kind": kind, "prompt": f"Prompt {i}", "prompt_meaning": "m", "item_id": item_id, "explanation": None, "answers": rows}


def situation(**over):
    return base("situation", **{"description": "d", "goal": "g", "setting": "s", "partner_name": "Ravi", "partner_role": "driver", "difficulty": 2,
                                "topic": {"id": 1, "slug": "food"}, "steps": [step(1, "learn_phrase"), step(2), step(3, "translate", ("one", "uno"))],
                                "items": {1: item(1)}, **over})


def listening(mode="choose_phrase", **over):
    return base("listening_activity", **{"mode": mode, "prompt": "Listen", "difficulty": 2, "item_id": 1, "topic": {"id": 1, "slug": "food"},
                                         "options": [{"id": 1, "item_id": 1, "sort_order": 1}, {"id": 2, "item_id": 2, "sort_order": 2}, {"id": 3, "item_id": 3, "sort_order": 3}],
                                         "items": {1: item(1), 2: item(2), 3: item(3)}, **over})


def found(findings):
    return sorted(f["code"] for f in findings)


def ex(snap, index=0, **over):
    snap = copy.deepcopy(snap)
    snap["exercises"][index].update(over)
    return snap


# ---------- clean content stays clean ----------
@pytest.mark.parametrize("snap,validate", [(lesson(), validate_lesson), (situation(), validate_situation), (listening(), validate_listening_activity),
                                           (listening("choose_meaning"), validate_listening_activity)])
def test_valid_content_has_no_findings(snap, validate):
    assert validate(snap) == []


def test_finding_shape_and_severity_come_from_the_catalogue():
    out = validate_lesson(lesson(exercises=[], topics=[]))
    assert out and all(set(f) == {"code", "severity", "entity", "message"} for f in out)
    assert all(f["severity"] == codes.FINDING_CODES[f["code"]] and f["message"] and f["entity"].startswith("lesson:1") for f in out)


# ---------- lessons ----------
LESSON_CASES = {
    "lesson_no_exercises": (lambda: lesson(exercises=[]), ["lesson_no_exercises"]),
    "lesson_no_topics": (lambda: lesson(topics=[]), ["lesson_no_topics"]),
    "lesson_no_vocabulary": (lambda: lesson(vocabulary_ids=[], items={1: item(1), 2: item(2)}), ["exercise_item_not_in_lesson", "exercise_item_not_in_lesson", "lesson_no_vocabulary"]),
    "lesson_duplicate_title": (lambda: lesson(sibling_title_count=1), ["lesson_duplicate_title"]),
    "exercise_mc_too_few_answers": (lambda: lesson(exercises=[mc(1, 1, answers=("only",))]), ["exercise_mc_too_few_answers"]),
    "exercise_mc_correct_count/none": (lambda: lesson(exercises=[ex(lesson(), 0, answers=[{"id": 1, "text": "a", "is_correct": False, "sort_order": 1}, {"id": 2, "text": "b", "is_correct": False, "sort_order": 2}])["exercises"][0]]),
                                       ["exercise_mc_correct_count"]),
    "exercise_mc_correct_count/two": (lambda: lesson(exercises=[mc(1, 1, answers=("a", "b", "c")) | {"answers": [{"id": n, "text": t, "is_correct": n < 2, "sort_order": n + 1} for n, t in enumerate("abc")]}]),
                                      ["exercise_mc_correct_count"]),
    "exercise_typed_no_accepted_answer": (lambda: lesson(exercises=[typed(1, 1, accepted=())]), ["exercise_typed_no_accepted_answer"]),
    "exercise_typed_incorrect_row": (lambda: lesson(exercises=[typed(1, 1, accepted=("one", "two")) | {"answers": [{"id": 1, "text": "one", "is_correct": True, "sort_order": 1}, {"id": 2, "text": "wrong", "is_correct": False, "sort_order": 2}]}]),
                                     ["exercise_typed_incorrect_row"]),
    "exercise_duplicate_answers": (lambda: lesson(exercises=[mc(1, 1, answers=("Water", "water.", "tea"))]), ["exercise_duplicate_answers"]),
    "exercise_duplicate_prompt": (lambda: lesson(exercises=[mc(1, 1) | {"prompt": "Same?"}, typed(2, 2) | {"prompt": "same"}]), ["exercise_duplicate_prompt"]),
    "exercise_invalid_difficulty/0": (lambda: lesson(exercises=[mc(1, 1, difficulty=0)]), ["exercise_invalid_difficulty"]),
    "exercise_invalid_difficulty/4": (lambda: lesson(exercises=[mc(1, 1, difficulty=4)]), ["exercise_invalid_difficulty"]),
    "exercise_item_missing": (lambda: lesson(exercises=[mc(1, None)]), ["exercise_item_missing"]),
    "exercise_item_not_in_lesson": (lambda: lesson(exercises=[mc(1, 3)], items={1: item(1), 2: item(2), 3: item(3)}), ["exercise_item_not_in_lesson"]),
    "vocabulary_unknown": (lambda: lesson(vocabulary_ids=[1, 2, 99]), ["vocabulary_unknown"]),
    "vocabulary_missing_english": (lambda: lesson(items={1: item(1), 2: item(2, en=None)}), ["vocabulary_missing_english"]),
    "vocabulary_missing_english/blank": (lambda: lesson(items={1: item(1), 2: item(2) | {"meaning_en": "   "}}), ["vocabulary_missing_english"]),
    "vocabulary_cefr_above_unit": (lambda: lesson(items={1: item(1), 2: item(2, rank=2)}), ["vocabulary_cefr_above_unit"]),
    "exercise_item_english": (lambda: lesson(vocabulary_ids=[1], exercises=[mc(1, 1), typed(2, 2)], items={1: item(1), 2: item(2, en=None)}), ["exercise_item_not_in_lesson", "vocabulary_missing_english"]),
}


@pytest.mark.parametrize("name", sorted(LESSON_CASES))
def test_lesson_rules(name):
    build, expected = LESSON_CASES[name]
    assert found(validate_lesson(build())) == sorted(expected)


@pytest.mark.parametrize("name,build", [
    ("two answers is enough for multiple choice", lambda: lesson(exercises=[mc(1, 1, answers=("a", "b"))])),
    ("two accepted answers for a typed exercise", lambda: lesson(exercises=[typed(1, 1, accepted=("one", "uno"))], vocabulary_ids=[1])),
    ("vocabulary at the lesson's own level", lambda: lesson(items={1: item(1, rank=1), 2: item(2, rank=1)})),
    ("a lower-level word in a higher-level lesson", lambda: lesson(cefr_rank=3, items={1: item(1, rank=1), 2: item(2, rank=2)})),
    ("difficulty 1 and 3", lambda: lesson(exercises=[mc(1, 1, difficulty=1), typed(2, 2) | {"difficulty": 3}])),
    ("fill_blank is a typed kind", lambda: lesson(exercises=[typed(1, 1, kind="fill_blank")], vocabulary_ids=[1])),
    ("empty age targeting means universal", lambda: lesson(age_group_ids=[])),
    ("one valid age group", lambda: lesson(age_group_ids=[2])),
    ("all three age groups", lambda: lesson(age_group_ids=[1, 2, 3])),
    ("a newline in the description", lambda: lesson(description="line one\nline two")),
    ("Devanagari with joiners is not a control character", lambda: lesson(title="नमस्ते‍")),
    ("answers that differ", lambda: lesson(exercises=[mc(1, 1, answers=("Water", "Wine"))])),
])
def test_lesson_boundaries_stay_clean(name, build):
    assert validate_lesson(build()) == [], name


# ---------- situations ----------
SITUATION_CASES = {
    "situation_no_steps": (lambda: situation(steps=[], items={}), ["situation_no_steps"]),
    "situation_topic_missing": (lambda: situation(topic=None), ["situation_topic_missing"]),
    "situation_invalid_difficulty/0": (lambda: situation(difficulty=0), ["situation_invalid_difficulty"]),
    "situation_invalid_difficulty/6": (lambda: situation(difficulty=6), ["situation_invalid_difficulty"]),
    "situation_duplicate_title": (lambda: situation(sibling_title_count=2), ["situation_duplicate_title"]),
    "step_choose_too_few_answers": (lambda: situation(steps=[step(1, answers=("only",))]), ["step_choose_too_few_answers"]),
    "step_choose_correct_count/none": (lambda: situation(steps=[step(1, answers=("a", "b"), correct=5)]), ["step_choose_correct_count"]),
    "step_choose_correct_count/two": (lambda: situation(steps=[step(1) | {"answers": [{"id": n, "text": t, "is_correct": True, "sort_order": n + 1} for n, t in enumerate("ab")]}]), ["step_choose_correct_count"]),
    "step_typed_no_accepted_answer/translate": (lambda: situation(steps=[step(1, "translate", ())]), ["step_typed_no_accepted_answer"]),
    "step_typed_no_accepted_answer/conversation": (lambda: situation(steps=[step(1, "conversation", ())]), ["step_typed_no_accepted_answer"]),
    "step_typed_no_accepted_answer/fill_blank": (lambda: situation(steps=[step(1, "fill_blank", ())]), ["step_typed_no_accepted_answer"]),
    "step_typed_incorrect_row": (lambda: situation(steps=[step(1, "translate") | {"answers": [{"id": 1, "text": "x", "is_correct": True, "sort_order": 1}, {"id": 2, "text": "y", "is_correct": False, "sort_order": 2}]}]), ["step_typed_incorrect_row"]),
    "step_duplicate_answers": (lambda: situation(steps=[step(1, answers=("Hello!", "hello"))]), ["step_duplicate_answers"]),
    "vocabulary_missing_english": (lambda: situation(items={1: item(1, en=None)}), ["vocabulary_missing_english"]),
    "vocabulary_cefr_above_unit": (lambda: situation(items={1: item(1, rank=2)}), ["vocabulary_cefr_above_unit"]),
    "vocabulary_unknown": (lambda: situation(items={}), ["vocabulary_unknown"]),
}


@pytest.mark.parametrize("name", sorted(SITUATION_CASES))
def test_situation_rules(name):
    build, expected = SITUATION_CASES[name]
    assert found(validate_situation(build())) == sorted(expected)


@pytest.mark.parametrize("name,build", [
    ("a learn_phrase step has no answers", lambda: situation(steps=[step(1, "learn_phrase")])),
    ("difficulty 1 and 5", lambda: situation(difficulty=5)),
    ("typed step with two accepted answers", lambda: situation(steps=[step(1, "translate", ("a", "b"))], items={})),
    ("a conversation step with suggestions", lambda: situation(steps=[step(1, "conversation", ("hi", "hello"))], items={})),
    ("a choose_response step with two answers", lambda: situation(steps=[step(1, answers=("a", "b"))], items={})),
])
def test_situation_boundaries_stay_clean(name, build):
    assert validate_situation(build()) == [], name


# ---------- listening ----------
LISTENING_CASES = {
    "listening_option_count/two": (lambda: listening(options=listening()["options"][:2]), ["listening_option_count"]),
    "listening_option_count/four": (lambda: listening(options=listening()["options"] + [{"id": 4, "item_id": 4, "sort_order": 4}], items={1: item(1), 2: item(2), 3: item(3), 4: item(4)}), ["listening_option_count"]),
    "listening_option_count/none": (lambda: listening(options=[]), ["listening_option_count", "listening_target_not_in_options"]),
    "listening_target_not_in_options": (lambda: listening(item_id=9, items={1: item(1), 2: item(2), 3: item(3), 9: item(9)}), ["listening_target_not_in_options"]),
    "listening_duplicate_option_text/meaning": (lambda: listening("choose_meaning", items={1: item(1), 2: item(2) | {"meaning_en": "Meaning1."}, 3: item(3)}), ["listening_duplicate_option_text"]),
    "listening_topic_missing": (lambda: listening(topic=None), ["listening_topic_missing"]),
    "listening_invalid_difficulty/0": (lambda: listening(difficulty=0), ["listening_invalid_difficulty"]),
    "listening_invalid_difficulty/4": (lambda: listening(difficulty=4), ["listening_invalid_difficulty"]),
    "listening_duplicate_title": (lambda: listening(sibling_title_count=1), ["listening_duplicate_title"]),
    "vocabulary_missing_english": (lambda: listening(items={1: item(1), 2: item(2, en=None), 3: item(3)}), ["vocabulary_missing_english"]),
    "vocabulary_cefr_above_unit": (lambda: listening(items={1: item(1), 2: item(2), 3: item(3, rank=3)}), ["vocabulary_cefr_above_unit"]),
}


@pytest.mark.parametrize("name", sorted(LISTENING_CASES))
def test_listening_rules(name):
    build, expected = LISTENING_CASES[name]
    assert found(validate_listening_activity(build())) == sorted(expected)


def test_duplicate_option_text_depends_on_the_mode():
    """Two options with the same meaning are fine when the learner reads the phrases, and a duplicate when the learner reads the meanings."""
    same_meaning = {1: item(1), 2: item(2) | {"meaning_en": "meaning1"}, 3: item(3)}
    assert validate_listening_activity(listening("choose_phrase", items=same_meaning)) == []
    assert found(validate_listening_activity(listening("choose_meaning", items=same_meaning))) == ["listening_duplicate_option_text"]
    same_text = {1: item(1), 2: item(2) | {"text": "Word1"}, 3: item(3)}
    assert found(validate_listening_activity(listening("choose_phrase", items=same_text))) == ["listening_duplicate_option_text"]
    assert validate_listening_activity(listening("choose_meaning", items=same_text)) == []


# ---------- rules shared by all three ----------
SHARED = [("lesson", lesson, validate_lesson), ("situation", situation, validate_situation), ("listening_activity", listening, validate_listening_activity)]


@pytest.mark.parametrize("kind,build,validate", SHARED)
@pytest.mark.parametrize("slug,ok", [("food", True), ("a", True), ("food-meaning", True), ("a1-b2", True), ("x" * 60, True), ("x" * 61, False), ("Food", False), ("food_meaning", False),
                                     ("-food", False), ("food-", False), ("food--meaning", False), ("food meaning", False), ("", False), ("नमस्ते", False), ("food/../x", False)])
def test_slug_format(kind, build, validate, slug, ok):
    assert ("slug_invalid" not in found(validate(build(slug=slug)))) is ok


@pytest.mark.parametrize("kind,build,validate", SHARED)
def test_shared_language_level_and_age_rules(kind, build, validate):
    assert found(validate(build(level_valid=False))) == ["language_level_invalid"]
    assert found(validate(build(age_group_ids=[9]))) == ["age_group_unknown"]
    assert found(validate(build(age_group_ids=[2, 2]))) == ["age_group_duplicate"]
    assert found(validate(build(age_group_ids=[9, 9]))) == ["age_group_duplicate", "age_group_unknown"]


@pytest.mark.parametrize("kind,build,validate", SHARED)
def test_lifecycle_findings(kind, build, validate):
    assert found(validate(build(status="archived", archived_at=None))) == ["lifecycle_archived_without_time"]
    assert found(validate(build(status="archived", archived_at="2026-01-01 00:00:00"))) == []
    assert found(validate(build(status="draft", archived_at="2026-01-01 00:00:00"))) == ["lifecycle_time_without_archive"]
    assert found(validate(build(status="published", archived_at="2026-01-01 00:00:00", published_at="2026-01-01 00:00:00"))) == ["lifecycle_time_without_archive"]
    assert found(validate(build(status="published", published_at=None))) == ["lifecycle_published_without_time"]
    assert validate(build(status="published", published_at="2026-01-01 00:00:00")) == []
    assert [f["severity"] for f in validate(build(status="published", published_at=None))] == ["warning"]


@pytest.mark.parametrize("kind,build,validate", SHARED)
def test_unpublished_dependency_chain(kind, build, validate):
    """No status-bearing dependency exists in the schema today, so the rule is exercised on a synthetic snapshot: any dependency that is not
    published (or is archived) blocks; published, or a dependency without a lifecycle (status None), does not."""
    assert found(validate(build(dependencies=[{"type": "lesson", "id": 5, "status": "draft"}]))) == ["dependency_unpublished"]
    assert found(validate(build(dependencies=[{"type": "lesson", "id": 5, "status": "archived"}]))) == ["dependency_unpublished"]
    assert found(validate(build(dependencies=[{"type": "lesson", "id": 5, "status": "published"}, {"type": "topic", "id": 1, "status": None}]))) == []
    two = validate(build(dependencies=[{"type": "lesson", "id": 5, "status": "draft"}, {"type": "situation", "id": 6, "status": "archived"}]))
    assert found(two) == ["dependency_unpublished"] * 2


def _control_cases():
    return {
        "lesson": [lesson(title="bad\x00title"), lesson(description="a\x07b"), lesson(tip="a\tb"), lesson(situation="x\rj"), ex(lesson(), 0, prompt="p\x1b"), ex(lesson(), 0, explanation="e\x08"),
                   ex(lesson(), 0, answers=[{"id": 1, "text": "a\x00", "is_correct": True, "sort_order": 1}, {"id": 2, "text": "b", "is_correct": False, "sort_order": 2}])],
        "situation": [situation(title="t\x00"), situation(goal="g\x01"), situation(partner_name="Ra\x02vi"), situation(steps=[step(1, answers=("a\x00", "b"))])],
        "listening": [listening(title="t\x00"), listening(prompt="p\x03")],
    }


@pytest.mark.parametrize("which,validate", [("lesson", validate_lesson), ("situation", validate_situation), ("listening", validate_listening_activity)])
def test_control_characters_are_found_in_every_text_field(which, validate):
    for snap in _control_cases()[which]:
        assert "text_control_characters" in found(validate(snap)), snap


def test_a_newline_is_allowed_only_where_the_field_is_multi_line():
    assert validators.has_control_characters("a\nb") is True
    assert validators.has_control_characters("a\nb", multiline=True) is False
    assert validators.has_control_characters("a\x00b", multiline=True) is True
    assert validators.has_control_characters("a\tb", multiline=True) is True
    assert validators.has_control_characters("title with ‘quotes’ and नमस्ते") is False
    assert validators.has_control_characters(None) is False
    assert found(validate_lesson(lesson(title="two\nlines"))) == ["text_control_characters"]            # a title is single-line
    assert found(validate_lesson(lesson(description="two\nlines"))) == []


# ---------- severity: errors block, warnings do not ----------
def test_errors_helper_keeps_only_blocking_findings():
    out = validate_lesson(lesson(sibling_title_count=1, exercises=[mc(1, None, answers=("a",))]))
    assert found(out) == ["exercise_item_missing", "exercise_mc_too_few_answers", "lesson_duplicate_title"]
    assert [f["code"] for f in validators.errors(out)] == ["exercise_mc_too_few_answers"]
    assert validators.errors([f for f in out if f["severity"] == "warning"]) == []


def test_every_warning_code_is_non_blocking_and_every_other_code_blocks():
    warnings = {c for c, s in codes.FINDING_CODES.items() if s == "warning"}
    assert warnings == {"lesson_duplicate_title", "exercise_item_missing", "exercise_item_not_in_lesson", "situation_duplicate_title", "listening_duplicate_title",
                        "lifecycle_published_without_time", "integrity_orphan_vocabulary", "integrity_orphan_topic"}
    assert set(codes.FINDING_CODES.values()) == {"error", "warning"}


# ---------- the catalogue is fully exercised ----------
def _emitted():
    emitted = set()
    for cases, validate in ((LESSON_CASES, validate_lesson), (SITUATION_CASES, validate_situation), (LISTENING_CASES, validate_listening_activity)):
        for build, _ in cases.values():
            emitted |= {f["code"] for f in validate(build())}
    for _, build, validate in SHARED:
        for over in ({"slug": "Bad"}, {"level_valid": False}, {"age_group_ids": [9, 9]}, {"status": "archived"}, {"archived_at": "x"}, {"status": "published"},
                     {"dependencies": [{"type": "x", "id": 1, "status": "draft"}]}):
            emitted |= {f["code"] for f in validate(build(**over))}
        for snap in _control_cases().get({"lesson": "lesson", "situation": "situation", "listening_activity": "listening"}[build().get("type")], []):
            emitted |= {f["code"] for f in validate(snap)}
    return emitted


def test_every_validator_code_is_reachable_and_nothing_undeclared_is_emitted():
    """The per-entity codes only: the integrity_* codes belong to the sweep and are driven from the database in test_admin_validation_api.py."""
    per_entity = {c for c in codes.FINDING_CODES if not c.startswith("integrity_")}
    assert _emitted() == per_entity


def test_options_without_an_english_meaning_are_reported_once_each_and_never_as_duplicates():
    """Two options that both lack the English text have no label at all: that is a missing-translation problem, not 'two options read the same'."""
    snap = listening("choose_meaning", items={1: item(1), 2: item(2, en=None), 3: item(3, en=None)})
    assert found(validate_listening_activity(snap)) == ["vocabulary_missing_english", "vocabulary_missing_english"]
