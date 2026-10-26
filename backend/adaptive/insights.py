"""Learning insights: short statements about the learner's own recent evidence, written by deterministic templates.

Every insight is made from evidence rows in the bundle and carries them. If the evidence is not there, the insight is not made: the
service returns "not enough evidence" rather than an empty or generic claim. A model may only REWORD an insight, and the reworded text is
accepted only if it contains exactly the numbers of the original (see validate_rewrite). Wording stays factual: no judgements about ability
or feelings."""
from .. import settings

SOURCE_WORDS = {"listening": "listening", "lesson": "lesson", "situation": "situation"}


def claims(bundle):
    """-> [{kind, subject, text, evidence_ids}] in a fixed order, at most AI_MAX_INSIGHTS."""
    out = []
    for e in bundle.where("accuracy"):
        d = e.data
        if d["prev_accuracy"] is None:
            continue
        delta = d["accuracy"] - d["prev_accuracy"]
        word = SOURCE_WORDS[d["source"]]
        if delta >= settings.AI_TREND_DELTA:
            out.append({"kind": "accuracy_trend", "subject": d["source"], "evidence_ids": [e.id],
                        "text": f"Your {word} accuracy has improved recently: {d['correct']} of {d['attempts']} right in your latest answers, up from {d['prev_correct']} of {d['prev_attempts']} before."})
        elif delta <= -settings.AI_TREND_DELTA:
            out.append({"kind": "accuracy_trend", "subject": d["source"], "evidence_ids": [e.id],
                        "text": f"Your {word} accuracy dipped recently: {d['correct']} of {d['attempts']} right in your latest answers, down from {d['prev_correct']} of {d['prev_attempts']} before."})
    for e in bundle.where("weakness"):
        d = e.data
        if d["rule"] == "low_topic_accuracy":
            out.append({"kind": "repeat_weakness", "subject": d["topic"], "evidence_ids": [e.id],
                        "text": f"You have been missing {d['topic_name']} questions: {d['incorrect']} wrong out of {d['attempts']} recent answers. "
                                f"Practising {d['topic_name']} vocabulary before another {d['topic_name']} roleplay may help."})
        else:
            out.append({"kind": "repeat_weakness", "subject": f"item-{d['item_id']}", "evidence_ids": [e.id],
                        "text": f"“{d['item_text']}” has been answered wrongly {d['incorrect']} of {d['attempts']} times."})
    for e in bundle.where("confidence"):
        for acc in bundle.where("accuracy", source="topic", topic=e.data["topic"]):
            if acc.data["accuracy"] >= 0.8:                                     # only where the same topic has solid recent accuracy: a stored fact, not a guess
                out.append({"kind": "confidence_gap", "subject": e.data["topic"], "evidence_ids": [e.id, acc.id],
                            "text": f"You rated your confidence in {e.data['topic_name']} at {e.data['score']}%, but {acc.data['correct']} of your last {acc.data['attempts']} "
                                    f"{e.data['topic_name']} answers were correct."})
    rps = bundle.where("roleplay")
    if rps:
        latest = rps[0]
        out.append({"kind": "roleplay_progress", "subject": "latest", "evidence_ids": [latest.id],
                    "text": f"In your latest roleplay (“{latest.data['title']}”) you got {latest.data['correct']} of {latest.data['total']} steps right."})
    for e in (x for x in bundle.where("activity") if "days" in x.data):
        out.append({"kind": "practice_gap", "subject": "gap", "evidence_ids": [e.id], "text": f"It has been {e.data['days']} days since your last answer."})
    return out[:settings.AI_MAX_INSIGHTS]
