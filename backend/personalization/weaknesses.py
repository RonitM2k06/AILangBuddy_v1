"""Weakness detection from the attempt history. Two transparent rules (thresholds in rules.py):

  low_topic_accuracy    in a topic, the learner's most recent answers are mostly wrong
                        (enough answers, enough mistakes, accuracy below the threshold);
  repeated_item_errors  the same vocabulary item has been answered wrongly several times and the latest
                        answer on it is still wrong.

A single mistake, or a couple of them, never produces a weakness. A weakness that stops holding is kept as
'resolved' rather than deleted, and comes back (reactivated) if the pattern returns."""
from ..db import connect
from ..repositories import personalization as repo, situations
from . import clock, rules
from .context import learner_context


def _topic_severity(accuracy):
    return "high" if accuracy < rules.TOPIC_HIGH_BELOW else "medium" if accuracy < rules.TOPIC_MEDIUM_BELOW else "low"


def _item_severity(incorrect):
    return "high" if incorrect >= rules.ITEM_HIGH_AT else "medium" if incorrect >= rules.ITEM_MEDIUM_AT else "low"


def detect(conn, user_id, language_id):
    """The weaknesses the current attempt history supports: [{rule, topic_id|item_id, severity, attempts, incorrect, last_evidence_at}]."""
    found = []
    for topic_id, w in repo.recent_topic_window(conn, user_id, language_id, rules.TOPIC_WINDOW).items():
        accuracy = (w["attempts"] - w["incorrect"]) / w["attempts"]
        if w["attempts"] >= rules.TOPIC_MIN_ATTEMPTS and w["incorrect"] >= rules.TOPIC_MIN_INCORRECT and accuracy < rules.TOPIC_WEAK_BELOW:
            found.append({"rule": "low_topic_accuracy", "topic_id": topic_id, "item_id": None, "severity": _topic_severity(accuracy),
                          "attempts": w["attempts"], "incorrect": w["incorrect"], "last_evidence_at": w["last_at"]})
    for s in repo.item_stats(conn, user_id, language_id):
        if s["incorrect"] >= rules.ITEM_MIN_INCORRECT and s["last_correct"] == 0:
            found.append({"rule": "repeated_item_errors", "topic_id": None, "item_id": s["item_id"], "severity": _item_severity(s["incorrect"]),
                          "attempts": s["attempts"], "incorrect": s["incorrect"], "last_evidence_at": s["last_at"]})
    return found


def refresh(conn, user_id, language_id):
    """Bring the stored weaknesses in line with the evidence: upsert the ones that hold, resolve the rest. Idempotent."""
    now = clock.now()
    found = detect(conn, user_id, language_id)
    for w in found:
        repo.upsert_weakness(conn, user_id, language_id, w["rule"], w["topic_id"], w["item_id"], w["severity"],
                             w["attempts"], w["incorrect"], w["last_evidence_at"], now)
    repo.resolve_weaknesses_except(conn, user_id, language_id, [w["topic_id"] for w in found if w["topic_id"] is not None],
                                   [w["item_id"] for w in found if w["item_id"] is not None], now)


def current(conn, user_id, ctx):
    """Active weaknesses, most severe first, with the evidence and a plain-language explanation."""
    rows = repo.active_weaknesses(conn, user_id, ctx["target_language_id"])
    items = situations.items_by_ids(conn, [r["item_id"] for r in rows if r["item_id"]], ctx["native_language_id"], ctx["fallback_id"])
    out = []
    for r in rows:
        correct = r["attempts"] - r["incorrect"]
        view = {"id": r["id"], "rule": r["rule"], "severity": r["severity"], "attempts": r["attempts"], "incorrect": r["incorrect"],
                "accuracy": round(correct / r["attempts"], 2), "last_evidence_at": r["last_evidence_at"], "detected_at": r["detected_at"]}
        if r["rule"] == "low_topic_accuracy":
            view["topic"] = {"slug": r["topic_slug"], "name": r["topic_name"], "icon": r["topic_icon"]}
            view["explanation"] = f"You answered {correct} of your last {r['attempts']} {r['topic_name']} questions correctly."
        else:
            it = items[r["item_id"]]
            view["item"] = {"id": it["id"], "text": it["text"], "pronunciation": it["pronunciation"], "meaning": it["meaning"]}
            view["explanation"] = (f"You have answered “{it['pronunciation'] or it['text']}” wrongly {r['incorrect']} times "
                                   f"out of {r['attempts']}, and your latest answer was still wrong.")
        out.append(view)
    return out


def list_weaknesses(db_path, user_id):
    with connect(db_path) as conn:  # one transaction: refresh the derived rows, then read them
        ctx = learner_context(conn, user_id)
        refresh(conn, user_id, ctx["target_language_id"])
        return current(conn, user_id, ctx)
