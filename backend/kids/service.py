"""The child adventure: levels built from the age-filtered listening activities, and a bounded lives system.

Levels are DERIVED (nothing about them is stored): the activities a child may see, grouped by topic in their usual order. A level
is completed when every one of its activities has a correct attempt, and unlocked when the level before it is completed. The
only stored game state is the number of lives (see repositories/kids.py). Answers go through the same grading and attempt
recording as the Listening feature (so they feed the existing weakness and confidence systems); a wrong one then costs a life in
the same transaction. Clients refer to levels, questions and choices by 1-based position, never by database id. No HTTP here."""
from .. import settings
from ..db import connect
from ..listening import service as listening
from ..personalization import clock
from ..personalization.context import Forbidden, InvalidInput, NeedsProfile, NotFound, learner_context  # noqa: F401  (re-exported)
from ..repositories import kids as repo, listening as listening_repo, situations
from . import lives as lives_rules

INSTRUCTION = {"choose_meaning": "Listen. Tap what it means.", "choose_phrase": "Listen. Tap what you heard."}


class Locked(Exception):
    """The level is not unlocked yet."""


class NoLives(Exception):
    def __init__(self, next_life_in):
        super().__init__("no lives left")
        self.next_life_in = next_life_in


def _child_context(conn, user_id):
    ctx = learner_context(conn, user_id)
    if ctx["age_group_code"] != "child":
        raise Forbidden()
    return ctx


def _now():
    return lives_rules.parse(clock.now())


def _lives(conn, user_id, now):
    """Brings the stored lives up to date (creating the row with full lives on first use) and returns the view."""
    if repo.get_state(conn, user_id) is None:
        repo.create_state(conn, user_id, settings.MAX_LIVES, lives_rules.fmt(now))
    state = repo.get_state(conn, user_id)
    count, anchor, wait = lives_rules.effective(state["lives"], lives_rules.parse(state["lives_updated_at"]), now)
    if (count, lives_rules.fmt(anchor)) != (state["lives"], state["lives_updated_at"]):
        repo.save_regenerated(conn, user_id, count, lives_rules.fmt(anchor))
    return {"current": count, "max": settings.MAX_LIVES, "next_life_in_seconds": wait}


def _levels(conn, user_id, ctx):
    """[{number, topic, icon, activities: [row...], stats: {id: stats}}], with status and progress filled in."""
    rows = listening_repo.list_available(conn, ctx["target_language_id"], ctx["max_rank"], ctx["age_group_id"])
    stats = listening_repo.activity_stats(conn, user_id, [r["id"] for r in rows])
    grouped = {}
    for r in rows:
        grouped.setdefault(r["topic_slug"], {"title": r["topic_name"], "icon": r["topic_icon"], "activities": []})["activities"].append(r)
    levels, previous_done = [], True
    for number, g in enumerate(grouped.values(), start=1):
        done = sum(1 for a in g["activities"] if (stats.get(a["id"]) or {}).get("correct"))
        total = len(g["activities"])
        status = "locked" if not previous_done else ("completed" if done == total else "open")
        levels.append({"number": number, **g, "done": done, "total": total, "status": status, "stats": stats})
        previous_done = previous_done and done == total
    return levels


def _level_summary(level):
    return {"number": level["number"], "title": level["title"], "icon": level["icon"], "status": level["status"],
            "done": level["done"], "total": level["total"]}


def _find(levels, number):
    if not 1 <= number <= len(levels):
        raise NotFound()
    return levels[number - 1]


def adventure(db_path, user_id):
    with connect(db_path) as conn:   # one transaction: regeneration may be written
        ctx = _child_context(conn, user_id)
        lives = _lives(conn, user_id, _now())
        levels = _levels(conn, user_id, ctx)
    return {"lives": lives, "levels": [_level_summary(l) for l in levels]}


def level(db_path, user_id, number):
    with connect(db_path) as conn:
        ctx = _child_context(conn, user_id)
        lives = _lives(conn, user_id, _now())
        lv = _find(_levels(conn, user_id, ctx), number)
        if lv["status"] == "locked":
            raise Locked()
        questions = []
        for k, a in enumerate(lv["activities"], start=1):
            options = listening_repo.options_for(conn, a["id"])
            items = situations.items_by_ids(conn, [o["item_id"] for o in options], ctx["native_language_id"], ctx["fallback_id"])
            views = listening._option_views(a["mode"], [(o["id"], o["item_id"]) for o in options], items)
            source = listening.AUDIO.resolve(conn, a["item_id"])
            questions.append({"number": k, "instruction": INSTRUCTION[a["mode"]], "audio": source.as_dict() if source else None,
                              "choices": [{"choice": j, **{key: v for key, v in view.items() if key != "id"}} for j, view in enumerate(views, start=1)],
                              "done": bool((lv["stats"].get(a["id"]) or {}).get("correct"))})
    return {"lives": lives, "level": _level_summary(lv), "questions": questions}


def answer(db_path, user_id, number, question, choice):
    with connect(db_path) as conn:   # one transaction: the graded attempt, the life lost and the regeneration are written together
        ctx = _child_context(conn, user_id)
        now = _now()
        lives = _lives(conn, user_id, now)
        lv = _find(_levels(conn, user_id, ctx), number)
        if lv["status"] == "locked":
            raise Locked()
        if not 1 <= question <= len(lv["activities"]):
            raise InvalidInput("question", "There is no such question in this level")
        activity = lv["activities"][question - 1]
        options = listening_repo.options_for(conn, activity["id"])
        if not 1 <= choice <= len(options):
            raise InvalidInput("choice", "There is no such choice")
        if lives["current"] <= 0:
            raise NoLives(lives["next_life_in_seconds"])
        result = listening.submit_in(conn, ctx, user_id, activity["id"], options[choice - 1]["id"], 0, None)
        if not result["correct"]:
            left = repo.lose_life(conn, user_id, lives_rules.fmt(now), settings.MAX_LIVES)
            if left is None:                       # the guarded UPDATE refused: nothing to take (cannot happen after the check above)
                raise NoLives(lives["next_life_in_seconds"])
            repo.record_loss(conn, user_id, result["attempt"]["id"], left, lives_rules.fmt(now))
        lives = _lives(conn, user_id, now)
        after = _levels(conn, user_id, ctx)
        refreshed = after[number - 1]
        correct_index = next(j for j, o in enumerate(options, start=1) if o["id"] == result["correct_option_id"])
        completed = refreshed["status"] == "completed"
        return {"correct": result["correct"], "correct_choice": correct_index, "lives": lives, "game_over": lives["current"] == 0,
                "heard": result["heard"], "level": _level_summary(refreshed), "level_completed": completed,
                "next_level_unlocked": completed and number < len(after)}
