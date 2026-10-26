"""Roleplay on top of the existing situations, for the authenticated learner. No HTTP and no SQL in here.

A roleplay walks the steps of a Phase 5 situation: nothing about the situation is copied. At each step the learner is told what to
achieve (never the answer), replies in their own words, and the SERVER decides whether the reply matches the stored answers; the
AI only voices the character and writes feedback text. The model answer stays hidden until the step is answered correctly or has
been missed three times. The provider is never sent the expected answer while the step is still open. If the provider fails, the
built-in one answers instead, so progress and evidence are never lost.

Roleplay is checked on WHAT was said. A spoken answer is accepted only as the transcript of one of the learner's own completed
speaking sessions (so the existing voice rules, the child restriction and any parent control, apply), and no pronunciation score is
ever produced here."""
import sqlite3

from .. import settings
from ..ai import registry, runner
from ..adaptive import semantic, service as adaptive_service
from ..adaptive.validate import validate_grade
from ..ai.base import AiError, RoleplayFeedbackRequest, RoleplayTurnRequest, SemanticGradeRequest, clean, clean_feedback
from ..db import connect
from ..gamification import service as gamification
from ..parent import controls as parent_controls
from ..personalization import clock, weaknesses
from ..personalization.context import Forbidden, InvalidInput, NeedsProfile, NotFound, learner_context  # noqa: F401  (re-exported)
from ..repositories import adaptive as adaptive_repo, gamification as game_repo, learner as learner_repo, pronunciation as pron_repo, roleplay as repo, situations, speaking as speaking_repo
from ..textnorm import answer_key

CHILD_MAX_CHARS = 100
HISTORY_TURNS = 6
LIST_LIMIT = 20


class Conflict(Exception):
    pass


# ---------- the situation, as a script ----------
def _available(conn, ctx, situation_id):
    return situations.get_available(conn, situation_id, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])


def _script(conn, ctx, situation_id, language):
    """[{step_id, objective, expected (set of normalised answers), model (the answer to reveal), item_id}] in order. SERVER ONLY."""
    steps = situations.steps_for_situation(conn, situation_id)
    code = _language_code(conn, ctx)                            # Marathi folds its documented spelling variants; Hindi is compared exactly
    items = situations.items_by_ids(conn, [s["item_id"] for s in steps if s["item_id"] and s["kind"] == "learn_phrase"], ctx["native_language_id"], ctx["fallback_id"])
    out = []
    for s in steps:
        if s["kind"] == "learn_phrase":
            it = items[s["item_id"]]
            raw = [x for x in (it["pronunciation"], it["text"]) if x]
            expected = {answer_key(x, code) for x in raw}
            model = f"{it['pronunciation']} ({it['text']})" if it["pronunciation"] else it["text"]
            objective = f"Say this in {language}: “{it['meaning']}”"
            first = (it["pronunciation"] or it["text"])
            item_id = s["item_id"]
        else:
            answers = [a for a in situations.answers_for_step(conn, s["id"]) if a["is_correct"]]
            raw = [a["answer_text"] for a in answers]
            expected = {answer_key(a["answer_text"], code) for a in answers}
            model = answers[0]["answer_text"]
            objective = s["prompt"]
            first = answers[0]["answer_text"]
            item_id = s["item_id"]
        out.append({"step_id": s["id"], "objective": objective, "expected": expected, "raw": raw, "model": model, "first": first, "item_id": item_id})
    return out


def _resolved(turns):
    return {t["step_id"]: t for t in turns if t["resolved"] != "no"}


def _current(script, turns):
    done = _resolved(turns)
    for i, step in enumerate(script):
        if step["step_id"] not in done:
            return i, step
    return None, None


def _hint(step, attempt_no):
    words = step["first"].split()
    if attempt_no == 1:
        return f"The phrase is {len(words)} word{'s' if len(words) != 1 else ''} long."
    return f"It starts with “{words[0]}”."


# ---------- views (never contain an answer before it is resolved) ----------
def _situation_view(sit):
    return {"id": sit["id"], "title": sit["title"], "setting": sit["setting"], "goal": sit["goal"],
            "partner_name": sit["partner_name"] or "Helper", "partner_role": sit["partner_role"]}


def _progress(script, turns, session):
    done = _resolved(turns)
    idx, step = _current(script, turns)
    return {"steps_total": len(script), "steps_resolved": len(done), "current_step": None if idx is None else idx + 1, "all_done": idx is None,
            "completed": session["status"] == "completed"}


def _grading_view(g):
    if g is None:
        return None
    return {"method": g["method"], "semantic_match": bool(g["semantic_match"]), "confidence": g["confidence"], "explanation": g["explanation"],
            "missing_objective": g["missing_objective"] or None, "grammar_feedback": g["grammar_feedback"] or None}


def _turn_view(t, script_by_step, grade=None):
    out = {"turn_no": t["turn_no"], "you": t["learner_text"], "input_mode": t["input_mode"], "character": t["character_reply"], "verdict": t["verdict"],
           "attempt_no": t["attempt_no"], "resolved": t["resolved"], "hint": t["hint"], "grading": _grading_view(grade)}
    if t["resolved"] != "no":
        out["model_answer"] = script_by_step[t["step_id"]]["model"]
    return out


def _session_view(conn, ctx, user_id, session, sit, script):
    turns = repo.turns(conn, user_id, session["id"])
    grades = adaptive_repo.grades_for_session(conn, user_id, session["id"])
    by_step = {s["step_id"]: s for s in script}
    idx, step = _current(script, turns)
    attempts = sum(1 for t in turns if step and t["step_id"] == step["step_id"])
    last_hint = next((t["hint"] for t in reversed(turns) if step and t["step_id"] == step["step_id"] and t["hint"]), None)
    return {"id": session["id"], "status": session["status"], "mode": session["mode"], "situation": _situation_view(sit),
            "scene": f"{sit['partner_name'] or 'Helper'}: {GREETING.get(_language_code(conn, ctx), 'Namaste')}! {sit['setting'] or sit['title']}. {sit['goal']}",
            "progress": _progress(script, turns, session),
            "current": None if step is None else {"objective": step["objective"], "attempts_used": attempts, "attempts_left": settings.ROLEPLAY_MAX_ATTEMPTS - attempts, "hint": last_hint},
            "turns": [_turn_view(t, by_step, grades.get(t["turn_no"])) for t in turns]}


def _language(conn, ctx):
    return conn.execute("SELECT name FROM languages WHERE id = ?", (ctx["target_language_id"],)).fetchone()["name"]


def _language_code(conn, ctx):
    return conn.execute("SELECT code FROM languages WHERE id = ?", (ctx["target_language_id"],)).fetchone()["code"]


# how the character greets you, in the language of the roleplay (Hindi's "Namaste" for any language without its own)
GREETING = {"hi": "Namaste", "mr": "Namaskar", "kn": "Namaskara", "ta": "Vanakkam", "fr": "Bonjour", "bn": "Nomoshkar", "te": "Namaskaram", "ur": "Assalaam alaikum", "ks": "Assalaam alaikum", "doi": "Namaste ji"}

EXACT = {"method": "exact", "semantic_match": True, "confidence": 1.0, "explanation": "Matches the expected phrase.", "missing_objective": "", "grammar_feedback": ""}


def _grade_answer(mode, language, language_code, cefr, step, learner_text, exact):
    """How the answer is judged, strictly in this order:
         1. an exact normalised match (the Phase 11 rule, unchanged);
         2. the deterministic semantic grader (built in, rule based, no model);
         3. an external grader, only for teens and adults, only when the deterministic grader was uncertain (SEMANTIC_LLM_FLOOR <= confidence < ACCEPT),
            and only believed at SEMANTIC_LLM_ACCEPT_AT or more. Its output is validated; if it is unusable the deterministic result stands.
       Nothing here can accept an answer the deterministic grader scored below the floor, and no explanation can contain a word of the key.
       -> (grade dict, provider label, fell_back)"""
    if exact:
        return dict(EXACT), "rules", False
    det = semantic.grade(language_code, learner_text, step["raw"])
    explanation, missing, grammar = semantic.explain(det)
    base = {"method": "semantic" if det.semantic_match else "none", "semantic_match": det.semantic_match, "confidence": det.confidence, "explanation": explanation,
            "missing_objective": missing, "grammar_feedback": grammar}
    if det.semantic_match or not det.supported or mode == "child" or det.confidence < settings.SEMANTIC_LLM_FLOOR:
        return base, "rules", False
    provider = registry.FACTORY()
    request = SemanticGradeRequest(language=language, language_code=language_code, cefr=cefr, objective=step["objective"], learner_text=learner_text,
                                   accepted=tuple(step["raw"]), det_confidence=det.confidence, det_coverage=det.coverage)
    try:
        out = validate_grade(runner.run(provider.semantic_grade, request), semantic.secret_words(step["raw"]), semantic.typed_words(learner_text))
    except AiError:
        return base, "rules", True
    if out["semantic_match"] and out["confidence"] >= settings.SEMANTIC_LLM_ACCEPT_AT:
        return {"method": "semantic_llm", **out}, provider.name[:32], False
    return base, "rules", False


# ---------- start / read ----------
def start(db_path, user_id, situation_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        sit = _available(conn, ctx, situation_id)
        if sit is None:
            raise NotFound()
        language = _language(conn, ctx)
        script = _script(conn, ctx, situation_id, language)
        if not script:
            raise NotFound()
        existing = repo.get_active_for_situation(conn, user_id, situation_id)
        resumed = existing is not None
        if not resumed:
            existing = repo.create_session(conn, user_id, situation_id, ctx["target_language_id"], sit["cefr_code"], ctx["age_group_code"], len(script), clock.now())
        return {"session": _session_view(conn, ctx, user_id, repo.get_session(conn, user_id, existing), sit, script)}, resumed


def get(db_path, user_id, session_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        session = repo.get_session(conn, user_id, session_id)
        if session is None:
            raise NotFound()
        sit = _available(conn, ctx, session["situation_id"])
        if sit is None:
            raise NotFound()
        return {"session": _session_view(conn, ctx, user_id, session, sit, _script(conn, ctx, session["situation_id"], _language(conn, ctx)))}


def list_sessions(db_path, user_id):
    with connect(db_path) as conn:
        learner_context(conn, user_id)
        return [{"id": s["id"], "title": s["title"], "status": s["status"], "steps_total": s["steps_total"], "created_at": s["created_at"], "completed_at": s["completed_at"]}
                for s in repo.list_sessions(conn, user_id, LIST_LIMIT)]


# ---------- a turn ----------
def _spoken_text(conn, ctx, user_id, speaking_session_id):
    parent_controls.require_voice(conn, ctx, user_id)             # the child restriction and any parent switch apply to spoken input
    row = speaking_repo.get_session(conn, user_id, speaking_session_id)
    if row is None:
        raise NotFound()
    if row["stage"] != "completed":
        raise Conflict("Record and transcribe your answer first.")
    t = pron_repo.best_transcript(conn, user_id, speaking_session_id)
    if t is None:
        raise Conflict("Record and transcribe your answer first.")
    return t["text"].strip()[:settings.AI_MAX_MESSAGE_CHARS]


def _history(turns):
    out = []
    for t in turns[-HISTORY_TURNS:]:
        out.append(("learner", t["learner_text"]))
        out.append(("character", t["character_reply"]))
    return tuple(out)


def _weak_phrases(db_path, user_id, script):
    wanted = {s["item_id"] for s in script if s["item_id"]}
    out = []
    for w in weaknesses.list_weaknesses(db_path, user_id) or []:
        if w["rule"] != "low_topic_accuracy" and w["item"]["id"] in wanted:
            out.append(f"{w['item']['text']} ({w['item']['pronunciation']})")
    return tuple(out[:3])


def turn(db_path, user_id, session_id, *, text=None, speaking_session_id=None, client_id=None):
    # --- step 1 (read) ---
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        session = repo.get_session(conn, user_id, session_id)
        if session is None:
            raise NotFound()
        sit = _available(conn, ctx, session["situation_id"])
        if sit is None:
            raise NotFound()
        mode = ctx["age_group_code"]
        if (text is None) == (speaking_session_id is None):
            raise InvalidInput("text", "Send either text or a spoken answer")
        if client_id is not None:
            stored = repo.find_turn_by_client_id(conn, user_id, session_id, client_id)
            if stored:
                script = _script(conn, ctx, session["situation_id"], _language(conn, ctx))
                return _result(conn, ctx, user_id, session, sit, script, stored, replayed=True)
        if session["status"] != "active":
            raise Conflict("This roleplay is finished.")
        if speaking_session_id is not None:
            learner_text, input_mode = _spoken_text(conn, ctx, user_id, speaking_session_id), "voice"
        else:
            learner_text, input_mode = text.strip(), "text"
        limit = CHILD_MAX_CHARS if mode == "child" else settings.AI_MAX_MESSAGE_CHARS
        if not learner_text or len(learner_text) > limit:
            raise InvalidInput("text", f"An answer must be 1-{limit} characters")
        language = _language(conn, ctx)
        script = _script(conn, ctx, session["situation_id"], language)
        turns = repo.turns(conn, user_id, session_id)
        idx, step = _current(script, turns)
        if step is None:
            raise Conflict("Every step is done. Complete the roleplay to see your feedback.")
        attempt_no = sum(1 for t in turns if t["step_id"] == step["step_id"]) + 1
        language_code, cefr = _language_code(conn, ctx), session["cefr_code"]
        exact = answer_key(learner_text, language_code) in step["expected"]
        history = _history(turns)
        situation = _situation_view(sit)
    grade, grade_provider, grade_fell_back = _grade_answer(mode, language, language_code, cefr, step, learner_text, exact)
    correct = grade["semantic_match"]
    verdict = "correct" if correct else "incorrect"
    missed = (not correct) and attempt_no >= settings.ROLEPLAY_MAX_ATTEMPTS
    resolved = "correct" if correct else ("missed" if missed else "no")
    hint = None
    if resolved == "no":
        close = f"You're close: {grade['missing_objective']}. " if grade["confidence"] >= settings.SEMANTIC_CLOSE_AT and grade["missing_objective"] else ""
        hint = (close + _hint(step, attempt_no))[:300]
    revealed = step["model"] if resolved != "no" else None             # the answer is sent to the provider only once it is no longer a secret
    nxt = script[idx + 1]["objective"] if resolved != "no" and idx + 1 < len(script) else None
    weak = () if mode == "child" else _weak_phrases(db_path, user_id, script)
    request = RoleplayTurnRequest(mode=mode, language=language, cefr=cefr, situation=situation, objective=step["objective"], learner_text=learner_text,
                                  verdict=verdict, attempt_no=attempt_no, hint=hint, revealed=revealed, history=history, weaknesses=weak, next_objective=nxt)
    # --- step 2: the character's line. A failure falls back to the built-in provider: the turn is judged by the server either way. ---
    provider = registry.offline() if mode == "child" else registry.FACTORY()
    provider_name = provider.name
    try:
        reply = clean(runner.run(provider.roleplay_reply, request), 1000)
    except AiError:
        provider_name = "builtin"
        reply = clean(registry.offline().roleplay_reply(request), 1000)
    # --- step 3 (write) ---
    now = clock.now()
    try:
        with connect(db_path) as conn:
            session = repo.get_session(conn, user_id, session_id)
            if session is None or session["status"] != "active":
                raise Conflict("This roleplay is finished.")
            turn_no = len(repo.turns(conn, user_id, session_id)) + 1
            turn_id = repo.insert_turn(conn, session_id, user_id, session["situation_id"], step["step_id"], turn_no, attempt_no, learner_text, input_mode, speaking_session_id,
                                       verdict, resolved, hint, reply, provider_name, client_id, now)
            adaptive_repo.insert_turn_grade(conn, user_id, turn_id, grade, grade_provider)
            if grade_fell_back:
                adaptive_repo.insert_event(conn, user_id, "grading_fallback", turn_id, "external grader unusable: deterministic result used", now)
            row = {"turn_no": turn_no, "step_id": step["step_id"], "attempt_no": attempt_no, "learner_text": learner_text, "input_mode": input_mode, "verdict": verdict,
                   "resolved": resolved, "hint": hint, "character_reply": reply, "provider": provider_name, "created_at": now}
            ctx2 = learner_context(conn, user_id)
            return _result(conn, ctx2, user_id, session, sit, script, row)
    except sqlite3.IntegrityError:
        with connect(db_path) as conn:
            stored = repo.find_turn_by_client_id(conn, user_id, session_id, client_id) if client_id else None
            if stored:
                return _result(conn, ctx, user_id, repo.get_session(conn, user_id, session_id), sit, script, stored, replayed=True)
        raise Conflict("That answer was already used or another answer arrived at the same time.")


def _result(conn, ctx, user_id, session, sit, script, row, replayed=False):
    turns = repo.turns(conn, user_id, session["id"])
    by_step = {s["step_id"]: s for s in script}
    grade = adaptive_repo.grades_for_session(conn, user_id, session["id"]).get(row["turn_no"])
    return {"turn": _turn_view(row, by_step, grade), "progress": _progress(script, turns, session), "replayed": replayed}


# ---------- completion and feedback ----------
def _evidence(script, turns):
    done = _resolved(turns)
    correct = [s for s in script if done[s["step_id"]]["resolved"] == "correct"]
    missed = [s for s in script if done[s["step_id"]]["resolved"] == "missed"]
    first_try = [s for s in correct if done[s["step_id"]]["attempt_no"] == 1]
    return correct, missed, first_try


def _feedback_view(f):
    return {"correctness": {"steps_total": f["steps_total"], "steps_correct": f["steps_correct"], "steps_missed": f["steps_missed"],
                            "first_try_correct": f["first_try_correct"], "summary": f["correctness_text"]},
            "vocabulary": f["vocabulary_feedback"], "grammar": f["grammar_feedback"], "hint": f["hint"], "encouragement": f["encouragement"],
            "next_step": f["next_step"], "pronunciation": {"available": False, "note": f["pronunciation_note"]}, "generated_by": f["provider"], "created_at": f["created_at"]}


def complete(db_path, user_id, session_id):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        session = repo.get_session(conn, user_id, session_id)
        if session is None:
            raise NotFound()
        stored = repo.get_feedback(conn, user_id, session_id)
        if stored:                                                            # completing twice returns the same feedback and pays nothing more
            return {"feedback": _feedback_view(stored), "xp_awarded": 0, "replayed": True, "remediation": []}
        sit = _available(conn, ctx, session["situation_id"])
        if sit is None:
            raise NotFound()
        script = _script(conn, ctx, session["situation_id"], _language(conn, ctx))
        turns = repo.turns(conn, user_id, session_id)
        idx, _ = _current(script, turns)
        if idx is not None:
            raise Conflict("Finish every step before completing the roleplay.")
        correct, missed, first_try = _evidence(script, turns)
        mode, cefr = ctx["age_group_code"], session["cefr_code"]
        voice_turns = sum(1 for t in turns if t["input_mode"] == "voice")
        language = _language(conn, ctx)
        situation = _situation_view(sit)
    request = RoleplayFeedbackRequest(mode=mode, language=language, cefr=cefr, situation=situation, steps_total=len(script), steps_correct=len(correct),
                                      steps_missed=len(missed), first_try_correct=len(first_try),
                                      missed=tuple({"objective": s["objective"], "answer": s["model"]} for s in missed), voice_turns=voice_turns)
    provider = registry.offline() if mode == "child" else registry.FACTORY()
    provider_name = provider.name
    try:
        texts = clean_feedback(runner.run(provider.roleplay_feedback, request))
    except AiError:
        provider_name = "builtin"
        texts = clean_feedback(registry.offline().roleplay_feedback(request))
    summary = f"{len(correct)} of {len(script)} steps correct ({len(first_try)} on the first try)."
    note = ("Some answers were spoken and turned into text by speech recognition. A roleplay checks what you said, not how it sounded, so there is no pronunciation score; "
            "use Voice Practice for that." if voice_turns else
            "You typed your answers, so there is no pronunciation feedback. Use Voice Practice to practise how it sounds.")
    now = clock.now()
    with connect(db_path) as conn:                                           # one transaction: the completion, the feedback and the XP credit
        if not repo.complete_session(conn, user_id, session_id, len(correct), len(missed), now):
            stored = repo.get_feedback(conn, user_id, session_id)
            if stored:
                return {"feedback": _feedback_view(stored), "xp_awarded": 0, "replayed": True, "remediation": []}
            raise Conflict("This roleplay is finished.")
        repo.insert_feedback(conn, session_id, user_id, {"steps_total": len(script), "steps_correct": len(correct), "steps_missed": len(missed), "first_try_correct": len(first_try),
                                                          "voice_turns": voice_turns, "correctness_text": summary, **texts, "pronunciation_note": note, "provider": provider_name}, now)
        before = game_repo.total_xp(conn, user_id)
        gamification.sync(conn, user_id)                                     # the existing XP ledger decides whether and how much; nothing is written here
        awarded = game_repo.total_xp(conn, user_id) - before
        remediation = adaptive_service.remediation_after_roleplay(conn, user_id, ctx, [s["item_id"] for s in missed if s["item_id"]], situation["title"], now, clock.today())
        return {"feedback": _feedback_view(repo.get_feedback(conn, user_id, session_id)), "xp_awarded": awarded, "replayed": False, "remediation": remediation}


def get_feedback(db_path, user_id, session_id):
    with connect(db_path) as conn:
        learner_context(conn, user_id)
        if repo.get_session(conn, user_id, session_id) is None:
            raise NotFound()
        stored = repo.get_feedback(conn, user_id, session_id)
        if stored is None:
            raise Conflict("The roleplay is not finished yet.")
        return {"feedback": _feedback_view(stored)}
