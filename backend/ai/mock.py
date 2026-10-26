"""The built-in provider: rule-based, deterministic and offline. It is what runs with no API key and in every test. It is NOT a
language model: it composes replies from the structured request it is given (stored facts, phrases from the learner's own
content, the server's verdict) and never states anything that is not in that request."""
from ..adaptive import ranking, semantic
from .base import InsightRewriteRequest, MicroLessonRequest, Provider, RankRequest, RoleplayFeedbackRequest, RoleplayTurnRequest, SemanticGradeRequest, TutorRequest

QUICK_PROMPTS = {
    "teach_me_a_phrase": "Teach me a new phrase",
    "say_it_again": "Say the last phrase again, slowly",
    "what_does_it_mean": "What does the last phrase mean?",
}


def _phrase(req, offset=0):
    if not req.phrases:
        return None
    return req.phrases[(req.turn_index + offset) % len(req.phrases)]


def _phrase_line(p):
    return f"{p['text']} ({p['pronunciation']}) means “{p['meaning']}”" if p.get("pronunciation") else f"{p['text']} means “{p['meaning']}”"


# The character's praise, by the language being learned (its name). A Marathi or Kannada learner never hears Hindi from the built-in character.
PRAISE = {"Hindi": ("Achha!", "Bilkul theek!", "Shabaash!"), "Marathi": ("Chhan!", "Ekdum barobar!", "Shabbas!"),
          "Kannada": ("Chennaagide!", "Sakkath!", "Bhale!"), "Tamil": ("Semma!", "Romba nalla!", "Super!"), "Bengali": ("Darun!", "Khub bhalo!", "Besh!"), "Telugu": ("Baagundi!", "Chaala baagundi!", "Super!"), "Urdu": ("Bahut khoob!", "Shabaash!", "Kya baat hai!"), "Kashmiri": ("Vaaray!", "Shaabaash!", "Aa, theek!"), "Dogri": ("Bada changa!", "Shabaash!", "Wah ji!"),
          "French": ("Très bien !", "Parfait !", "Bravo !")}


class MockProvider(Provider):
    name = "mock"

    # ----- tutor -----
    def tutor_reply(self, req: TutorRequest) -> str:
        if req.mode == "child":
            return self._child(req)
        text = req.message.lower()
        facts = "; ".join(req.facts[:3]) if req.facts else "I don't have any practice records for you yet"
        if any(w in text for w in ("hint", "stuck", "help")):
            where = f" in “{req.context_title}”" if req.context_title else ""
            advice = f"Take it one phrase at a time{where}. Say it out loud, then try to use it in a sentence of your own."
        elif any(w in text for w in ("mistake", "wrong", "why", "explain")):
            advice = ("Look at the answer you gave next to the correct one and find the first word that differs; "
                      "that is usually where the mistake started. Then repeat the correct phrase three times.")
        elif any(w in text for w in ("speak", "say", "pronounce", "practice", "practise")):
            advice = "Speaking out loud helps most. Try the Voice Practice page, or say the phrase below to yourself a few times."
        else:
            advice = "A short daily session beats a long occasional one. Pick one topic and finish it today."
        p = _phrase(req)
        suggestion = f" Try this phrase in {req.language}: {_phrase_line(p)}." if p else ""
        level = f"At level {req.cefr}, keep your sentences short and simple."
        return f"From your records: {facts}.\nAdvice (generated, not a record): {advice}{suggestion} {level}"

    def _child(self, req: TutorRequest) -> str:
        if not req.phrases:
            return "I don't have a new phrase for you yet. Try a Listening game!"
        if req.quick_prompt == "say_it_again":
            p = _phrase(req, -1)
            return "Say it slowly: " + " ... ".join((p.get("pronunciation") or p["text"]).split()) + "."
        if req.quick_prompt == "what_does_it_mean":
            p = _phrase(req, -1)
            return f"{p['text']} means “{p['meaning']}”."
        p = _phrase(req)
        return f"Here is a new phrase: {_phrase_line(p)}. Can you say it?"

    # ----- roleplay -----
    def roleplay_reply(self, req: RoleplayTurnRequest) -> str:
        who = req.situation.get("partner_name") or "Helper"
        if req.verdict == "correct":
            praise = PRAISE.get(req.language, PRAISE["Hindi"])[(req.attempt_no - 1) % 3]   # in the language of the roleplay
            more = f" Next: {req.next_objective}" if req.next_objective else " That was the last one!"
            return f"{who}: {praise} That works.{more}"
        if req.revealed:
            return f"{who}: No worries, let's move on. A natural way to say it: {req.revealed}"
        return f"{who}: Hmm, I didn't quite catch that. {req.hint}" if req.hint else f"{who}: Hmm, I didn't quite catch that. Try again."

    def roleplay_feedback(self, req: RoleplayFeedbackRequest) -> dict:
        if req.missed:
            vocab = "Phrases to practise again: " + "; ".join(f"{m['answer']} ({m['objective']})" for m in req.missed[:5]) + "."
        else:
            vocab = "You used the expected phrase for every step."
        grammar = ("This check compares your answers with the expected phrases, so I can't judge grammar in more detail "
                   "than whether each answer matched.")
        ratio = req.steps_correct / req.steps_total
        if ratio == 1:
            enc = "Excellent work, you got every step."
        elif ratio >= 0.5:
            enc = "Good effort. You got most of it, and practice will close the gap."
        else:
            enc = "Roleplays are hard at first. Every try teaches you something."
        hint = ("Try answering without looking back at the phrases." if req.first_try_correct == req.steps_total
                else "Say the phrases you missed out loud before trying again.")
        nxt = f"Try the “{req.situation['title']}” roleplay again" if req.steps_missed else "Move on to another situation"
        return {"vocabulary_feedback": vocab, "grammar_feedback": grammar, "hint": hint, "encouragement": enc, "next_step": nxt + "."}

    # ----- Phase 12 -----
    def semantic_grade(self, req: SemanticGradeRequest) -> dict:
        """The built-in grader: exactly the deterministic rule-based comparison (no model), expressed as a provider answer."""
        g = semantic.grade(req.language_code, req.learner_text, req.accepted)
        explanation, missing, grammar = semantic.explain(g)
        return {"semantic_match": g.semantic_match, "confidence": g.confidence, "explanation": explanation, "missing_objective": missing, "grammar_feedback": grammar}

    def generate_micro_lesson(self, req: MicroLessonRequest) -> dict:
        item = req.item
        phrase = item.get("pronunciation") or item["text"]
        if req.kind == "translation":
            answers = [a for a in (item.get("pronunciation"), item["text"]) if a]
            return {"question": f"Write this in {req.language}: \u201c{item['meaning']}\u201d", "answers": answers}
        if req.kind == "vocab_choice":
            correct, wrong, question = item["meaning"], list(req.distractors), f"What does \u201c{phrase}\u201d mean?"
        else:
            correct, wrong, question = phrase, list(req.distractors), f"Which phrase means \u201c{item['meaning']}\u201d?"
        options = wrong[:3]
        idx = sum(map(ord, phrase)) % (len(options) + 1)                                  # a stable, item-dependent place for the right answer
        options.insert(idx, correct)
        return {"question": question, "options": options, "answer_index": idx}

    def rewrite_insight(self, req: InsightRewriteRequest) -> str:
        return req.base_text                                                              # the built-in provider keeps the server's own wording

    def rank_recommendations(self, req: RankRequest) -> list:
        return [{"id": cid, "note": note} for cid, note in ranking.order(list(req.candidates))]
