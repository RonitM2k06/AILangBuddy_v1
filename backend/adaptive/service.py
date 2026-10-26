"""The adaptive layer for the authenticated learner: recommendations, insights, micro-lessons and the adaptive plan. No HTTP and no SQL here.

The shape of every operation is the same, and it is what keeps AI from becoming a source of truth:
  1. READ (one short transaction): learner context and the evidence bundle, built by deterministic code from stored rows.
  2. DECIDE by rules: which candidates exist, which claims are supported. Eligibility (level, age group, language, voice rules) is decided here.
  3. ASK a provider, with no transaction open, only to rank, reword or draft. Children only ever get the built-in provider.
  4. VALIDATE what came back. Invalid output is dropped and the deterministic result is used (and a short audit event is stored).
  5. WRITE (one transaction): only validated content, with the evidence that justifies it.
Nothing here awards XP or changes a level, a streak, a freeze or the CEFR level."""
import sqlite3

from .. import settings
from ..ai import registry, runner
from ..ai.base import AiError, InsightRewriteRequest, RankRequest
from ..db import connect
from ..parent import controls as parent_controls
from ..personalization import clock, plan as phase6_plan
from ..personalization.context import Forbidden, InvalidInput, NeedsProfile, NotFound, learner_context  # noqa: F401  (re-exported)
from ..repositories import adaptive as repo, curriculum, listening as listening_repo, situations
from ..textnorm import normalize
from . import engine, insights as insight_rules, microlessons, ranking
from .validate import validate_ranking, validate_rewrite

PHASE6_KINDS = ("review_topic", "review_item", "continue_lesson", "continue_situation", "low_confidence", "confidence_checkin", "next_lesson", "next_situation")
PLAN_ITEMS = 3


class Conflict(Exception):
    pass


def _provider(mode):
    return registry.offline() if mode == "child" else registry.FACTORY()


def _source(provider):
    return "llm" if provider.name == "llm" else "mock"


def _language(conn, ctx, user_id):
    name = conn.execute("SELECT name FROM languages WHERE id = ?", (ctx["target_language_id"],)).fetchone()["name"]
    return name, conn.execute("SELECT cefr_level FROM learner_profiles WHERE user_id = ?", (user_id,)).fetchone()["cefr_level"]


def _read(db_path, user_id):
    """Step 1+2: context, evidence and rule-made candidates from one consistent read."""
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        mode = ctx["age_group_code"]
        now, day = clock.now(), clock.today()
        prep = engine.prepare(conn, user_id, ctx, day, mode)
        language, cefr = _language(conn, ctx, user_id)
        jobs = []
        allowance = max(0, settings.AI_MAX_NEW_MICRO_LESSONS_PER_DAY - repo.count_micro_created_on(conn, user_id, day))
        for spec in prep["micro_specs"]:
            job = microlessons.plan(conn, user_id, ctx, spec, mode, day, prep["difficulty"]["recommended"])
            if job is None:
                continue
            if not job["reuse"]:
                if allowance <= 0:
                    continue
                allowance -= 1
            jobs.append(job)
        stored = _stored_remediation(conn, user_id, day, prep["bundle"])
    return {"ctx": ctx, "mode": mode, "now": now, "day": day, "language": language, "cefr": cefr, "prep": prep, "jobs": jobs, "remediation": stored}


def _stored_remediation(conn, user_id, day, bundle):
    """Today's still-active remediation suggestions (made when a roleplay was completed) stay candidates, with their stored evidence."""
    out = []
    for r in repo.list_recommendations(conn, user_id, day, ("active",)):
        if r["kind"] != "remediation":
            continue
        ids = [bundle.add(e["kind"], e["text"]) for e in repo.evidence_for(conn, user_id, "recommendation", r["id"])]
        out.append({"id": f"remediation:micro_lesson:{r['target_id']}", "kind": "remediation", "target_type": "micro_lesson", "target_id": r["target_id"], "title": r["title"],
                    "reason": r["reason"], "evidence_ids": ids, "boost": 0})
    return out


def _ensure_micro(db_path, user_id, state):
    """Steps 3-5 for micro-lessons: draft (provider, no transaction), validate, store. -> [(spec, micro_id, phrase)]."""
    mode, ctx = state["mode"], state["ctx"]
    drafted = []
    for job in state["jobs"]:
        if job["reuse"]:
            drafted.append((job, None))
            continue
        drafted.append((job, microlessons.generate(job, mode)))
    results, rejections = [], []
    with connect(db_path) as conn:
        for job, made in drafted:
            if job["reuse"]:
                results.append((job["spec"], job["micro_id"], job["phrase"]))
                continue
            validated, generator, rejected = made
            if rejected:
                repo.insert_event(conn, user_id, "micro_lesson_rejected", job["item_id"], f"provider output rejected: {rejected}", state["now"])
            try:
                # a drill's evidence must never quote the phrase the drill asks for: it would give the answer away
                evidence = [(e.kind, e.text.replace(f"\u201c{job['phrase']}\u201d", "This phrase")) for e in (state["prep"]["bundle"].get(i) for i in job["spec"]["evidence_ids"])]
                mid = microlessons.store(conn, user_id, ctx, job, validated, generator, evidence, mode, state["day"], state["now"], state["prep"]["difficulty"]["recommended"])
            except sqlite3.IntegrityError:                                         # a concurrent request stored today's drill first
                mid = repo.find_micro(conn, user_id, state["day"], job["item_id"], job["kind"])
                if mid is None:
                    continue
            results.append((job["spec"], mid, job["phrase"]))
    return results


def _micro_candidates(state, micro):
    bundle, out = state["prep"]["bundle"], []
    topics_with_roleplay = {s["topic_slug"]: s for s in state["prep"]["situations"]}
    for spec, mid, phrase in micro:
        reason = f"{bundle.get(spec['evidence_ids'][0]).text} A short drill can help."
        slug = spec.get("topic_slug")
        if slug and slug in topics_with_roleplay:
            name = topics_with_roleplay[slug]["topic_name"]
            reason = f"{bundle.get(spec['evidence_ids'][0]).text} Practise {name} vocabulary before attempting another {name} roleplay."
        out.append({"id": f"targeted_vocabulary:micro_lesson:{mid}", "kind": "targeted_vocabulary", "target_type": "micro_lesson", "target_id": mid, "title": f"Practice drill: “{phrase}”",
                    "reason": reason, "evidence_ids": list(spec["evidence_ids"]), "boost": spec["boost"]})
    return out


def _rank(db_path, user_id, state, cands):
    """Step 3-4 for ranking. -> ([(candidate, note)] best first, source, fell_back)."""
    bundle, mode = state["prep"]["bundle"], state["mode"]
    evidence = {c["id"]: bundle.texts(c["evidence_ids"]) for c in cands}
    req = RankRequest(mode=mode, language=state["language"], cefr=state["cefr"], base_order=tuple(c["id"] for c in cands),
                      candidates=tuple({"id": c["id"], "kind": c["kind"], "title": c["title"], "reason": c["reason"], "evidence": tuple(evidence[c["id"]]), "boost": c["boost"]} for c in cands))
    if not cands:
        return [], "rules", False
    provider = _provider(mode)
    by_id = {c["id"]: c for c in cands}
    try:
        ranked = validate_ranking(runner.run(provider.rank_recommendations, req), evidence)
        source, fell_back = _source(provider), False
    except AiError:
        ranked, source, fell_back = ranking.order(cands), "rules", True
    placed = {cid for cid, _ in ranked}
    for cid, note in ranking.order([c for c in cands if c["id"] not in placed]):          # a ranker may reorder, never drop: the rest follow in rule order
        ranked.append((cid, note))
    return [(by_id[cid], note or None) for cid, note in ranked], source, fell_back


# ---------- recommendations ----------
def _rec_view(conn, user_id, r):
    return {"id": r["id"], "rank": r["rank"], "kind": r["kind"], "title": r["title"], "reason": r["reason"], "ai_note": r["note"], "status": r["status"], "source": r["source"],
            "target": {"type": r["target_type"], "id": r["target_id"]}, "evidence": repo.evidence_for(conn, user_id, "recommendation", r["id"]), "generated": True}


def recommendations(db_path, user_id):
    state = _read(db_path, user_id)
    micro = _ensure_micro(db_path, user_id, state)
    cands = state["prep"]["candidates"] + _micro_candidates(state, micro) + state["remediation"]
    ranked, source, fell_back = _rank(db_path, user_id, state, cands)
    ranked = ranked[:settings.AI_MAX_RECOMMENDATIONS]
    ctx, day, now, mode = state["ctx"], state["day"], state["now"], state["mode"]
    bundle = state["prep"]["bundle"]
    with connect(db_path) as conn:
        keep = []
        for rank, (c, note) in enumerate(ranked, start=1):
            existing = repo.find_recommendation(conn, user_id, day, c["kind"], c["target_type"], c["target_id"])
            if existing:
                repo.update_active_ranking(conn, user_id, existing["id"], rank, note, source, c["reason"], c["title"])
                keep.append(existing["id"])
                continue
            rid = repo.insert_recommendation(conn, user_id, ctx["target_language_id"], day, c, rank, source, mode, now)
            repo.insert_evidence(conn, user_id, "recommendation", rid, [(bundle.get(i).kind, bundle.get(i).text) for i in c["evidence_ids"]])
            repo.update_active_ranking(conn, user_id, rid, rank, note, source, c["reason"], c["title"])
            keep.append(rid)
        for r in repo.list_recommendations(conn, user_id, day, ("applied",)):
            keep.append(r["id"])
        repo.expire_recommendations(conn, user_id, day, keep)
        if fell_back:
            repo.insert_event(conn, user_id, "ranking_fallback", None, "provider ranking unusable: deterministic order used", now)
        rows = [r for r in repo.list_recommendations(conn, user_id, day) if r["id"] in keep]
        views = [_rec_view(conn, user_id, r) for r in rows]
    return {"date": day, "mode": mode, "recommendations": views, "enough_evidence": bool(views),
            "message": None if views else "Not enough evidence yet to suggest anything. Keep practising and this will fill in."}


def _link(r):
    t, i = r["target_type"], r["target_id"]
    return {"lesson": f"#/lessons/{i}", "situation": f"#/situations/{i}", "roleplay": "#/ai-roleplay", "listening_activity": f"#/listening/{i}", "speaking": "#/voice",
            "topic": "#/confidence", "micro_lesson": "#/ai-insights"}[t]


def _still_eligible(conn, user_id, ctx, r):
    lang, rank, age = ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"]
    t, i = r["target_type"], r["target_id"]
    if t == "lesson":
        return curriculum.get_available_lesson(conn, i, lang, rank, age) is not None
    if t in ("situation", "roleplay"):
        return situations.get_available(conn, i, lang, rank, age) is not None
    if t == "listening_activity":
        return listening_repo.get_available(conn, i, lang, rank, age) is not None
    if t == "speaking":
        return parent_controls.voice_block_reason(conn, ctx, user_id) is None
    if t == "micro_lesson":
        return microlessons_visible(conn, user_id, ctx, i)
    return True


def microlessons_visible(conn, user_id, ctx, micro_id):
    m = repo.get_micro(conn, user_id, micro_id)
    return bool(m and m["status"] == "validated" and m["expires_at"] > clock.now() and m["language_id"] == ctx["target_language_id"] and m["mode"] == ctx["age_group_code"])


def apply(db_path, user_id, rec_id):
    """Marks a suggestion as taken and says where to go. Idempotent. It changes nothing about progress, XP, the plan or the CEFR level."""
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        r = repo.get_recommendation(conn, user_id, rec_id)
        if r is None:
            raise NotFound()
        if r["status"] == "expired" or r["plan_date"] != clock.today() and r["status"] != "applied":
            raise Conflict("This suggestion is no longer current.")
        if not _still_eligible(conn, user_id, ctx, r):
            raise Conflict("This suggestion is no longer available to you.")
        first = repo.mark_applied(conn, user_id, rec_id, clock.now())
        if first:
            repo.insert_event(conn, user_id, "recommendation_applied", rec_id, r["kind"], clock.now())
        fresh = repo.get_recommendation(conn, user_id, rec_id)
        return {"recommendation": _rec_view(conn, user_id, fresh), "go_to": _link(fresh), "already_applied": not first}


# ---------- insights ----------
def insights(db_path, user_id):
    state = _read(db_path, user_id)
    mode, bundle = state["mode"], state["prep"]["bundle"]
    claims = insight_rules.claims(bundle)
    texts, fallback = {}, False
    provider = None if mode == "child" else registry.FACTORY()                 # children get the server's own wording, never a provider
    for c in claims:
        ev = tuple(bundle.texts(c["evidence_ids"]))
        text, src = c["text"], "rules"
        if provider is not None:
            try:
                text = validate_rewrite(runner.run(provider.rewrite_insight, InsightRewriteRequest(mode, state["language"], c["kind"], c["text"], ev)), c["text"], ev)
                src = _source(provider)
            except AiError:
                text, src, fallback = c["text"], "rules", True
        texts[(c["kind"], c["subject"])] = (text, src, c)
    ctx, day, now = state["ctx"], state["day"], state["now"]
    with connect(db_path) as conn:
        for (kind, subject), (text, src, c) in texts.items():
            iid = repo.insert_insight(conn, user_id, ctx["target_language_id"], day, kind, subject, text, src, now)
            if iid:
                repo.insert_evidence(conn, user_id, "insight", iid, [(bundle.get(i).kind, bundle.get(i).text) for i in c["evidence_ids"]])
        if fallback:
            repo.insert_event(conn, user_id, "insight_fallback", None, "provider wording unusable: the server's own wording used", now)
        rows = [r for r in repo.list_insights(conn, user_id, day) if (r["kind"], r["subject"]) in texts]            # only claims the CURRENT evidence still supports
        views = [{"id": r["id"], "kind": r["kind"], "text": r["text"], "source": r["source"], "evidence": repo.evidence_for(conn, user_id, "insight", r["id"]), "generated": r["source"] != "rules"}
                 for r in rows]
    return {"date": day, "insights": views, "enough_evidence": bool(views),
            "message": None if views else "Not enough evidence yet to say anything about your progress."}


# ---------- micro-lessons ----------
def micro_lessons(db_path, user_id):
    state = _read(db_path, user_id)
    _ensure_micro(db_path, user_id, state)
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        rows = microlessons.presentable(conn, user_id, ctx, ctx["age_group_code"], clock.now())
        stats = repo.attempt_stats(conn, user_id, [m["id"] for m in rows])
        return {"micro_lessons": [microlessons.view(conn, user_id, m, stats.get(m["id"], {})) for m in rows]}


def answer_micro_lesson(db_path, user_id, micro_id, *, choice=None, text=None):
    with connect(db_path) as conn:
        ctx = learner_context(conn, user_id)
        if not microlessons_visible(conn, user_id, ctx, micro_id):
            raise NotFound()
        m = repo.get_micro(conn, user_id, micro_id)
        options = repo.options_for(conn, user_id, micro_id)
        if (choice is None) == (text is None):
            raise InvalidInput("choice", "Send either choice or text")
        if m["kind"] == "translation":
            if text is None or not text.strip() or len(text.strip()) > settings.AI_MAX_MESSAGE_CHARS:
                raise InvalidInput("text", f"Type your answer (1-{settings.AI_MAX_MESSAGE_CHARS} characters)")
            given = text.strip()
            correct = normalize(given) in {normalize(o["text"]) for o in options}
            shown = next(o["text"] for o in options)
            repo.insert_attempt(conn, user_id, micro_id, None, given, correct, clock.now())
        else:
            picked = next((o for o in options if o["ord"] == choice), None) if choice is not None else None
            if picked is None:
                raise InvalidInput("choice", "That is not one of the options")
            correct = bool(picked["is_correct"])
            shown = next(o["text"] for o in options if o["is_correct"])
            repo.insert_attempt(conn, user_id, micro_id, picked["ord"], None, correct, clock.now())
        repo.insert_event(conn, user_id, "micro_lesson_answered", micro_id, "correct" if correct else "incorrect", clock.now())
        return {"correct": correct, "correct_answer": shown, "note": "Practice only: this does not change your lessons, XP or level."}


# ---------- the adaptive plan ----------
def adaptive_plan(db_path, user_id):
    """The Phase 6 plan stays exactly as it is. Its candidates (the Phase 6 recommendations, all eligible by construction) are ranked and explained here."""
    phase6 = phase6_plan.get_plan(db_path, user_id)
    state = _read(db_path, user_id)
    cands = [c for c in state["prep"]["candidates"] if c["kind"] in PHASE6_KINDS]
    ranked, source, _ = _rank(db_path, user_id, state, cands)
    bundle = state["prep"]["bundle"]
    tasks = {(t["target"]["type"], t["target"]["id"]): t for t in phase6["tasks"]}
    items = []
    for place, (c, note) in enumerate(ranked[:PLAN_ITEMS], start=1):
        t = tasks.get((c["target_type"], c["target_id"]))
        items.append({"rank": place, "kind": c["kind"], "title": c["title"], "reason": c["reason"], "ai_note": note, "target": {"type": c["target_type"], "id": c["target_id"]},
                      "evidence": [{"kind": bundle.get(i).kind, "text": bundle.get(i).text} for i in c["evidence_ids"]], "in_phase6_plan": t is not None,
                      "status": t["status"] if t else None})
    return {"date": phase6["date"], "source": source, "mode": state["mode"], "items": items, "phase6_plan": {"generated": phase6["generated"], "done": phase6["done"], "total": phase6["total"]},
            "enough_evidence": bool(items)}


# ---------- after a roleplay ----------
def remediation_after_roleplay(conn, user_id, ctx, item_ids, situation_title, now, day):
    """For phrases the learner MISSED in a roleplay: a deterministic template drill for each (never a provider: this runs inside the completion
    transaction, and children must not get generated content), plus a 'remediation' suggestion pointing at it. -> suggestion views."""
    from ..ai.base import AiError as _E  # noqa: F401
    from .validate import validate_micro_lesson
    mode, views, seen = ctx["age_group_code"], [], set()
    for item_id in item_ids:
        if item_id in seen or len(seen) >= 3:
            continue
        seen.add(item_id)
        job = microlessons.plan(conn, user_id, ctx, {"item_id": item_id, "evidence_ids": []}, mode, day, 1)
        if job is None:
            continue
        evidence = [("roleplay", f"A step of the \u201c{situation_title}\u201d roleplay was missed.")]
        if job["reuse"]:
            mid = job["micro_id"]
        else:
            validated = validate_micro_lesson(registry.offline().generate_micro_lesson(job["request"]), job["kind"], job["canonical"], job["wrong"])
            mid = microlessons.store(conn, user_id, ctx, job, validated, "template", evidence, mode, day, now, 1)
        cand = {"kind": "remediation", "target_type": "micro_lesson", "target_id": mid, "title": f"Practice drill: \u201c{job['phrase']}\u201d",
                "reason": "You missed this phrase in a roleplay. A short drill can help before you try again."}
        row = repo.find_recommendation(conn, user_id, day, "remediation", "micro_lesson", mid)
        if row is None:
            rid = repo.insert_recommendation(conn, user_id, ctx["target_language_id"], day, cand, 1, "rules", mode, now)
            repo.insert_evidence(conn, user_id, "recommendation", rid, evidence)
            repo.insert_event(conn, user_id, "remediation_created", rid, "after roleplay", now)
            row = repo.get_recommendation(conn, user_id, rid)
        views.append(_rec_view(conn, user_id, row))
    return views
