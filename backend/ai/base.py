"""The AI provider interface. Domain code (tutor, roleplay) talks to this and nothing else: no vendor, URL or key appears
outside the adapters. A provider receives a small, already-bounded request object and returns plain text (or, for roleplay
feedback, a handful of short texts). Whatever it returns is validated and bounded by `clean` before it is stored or shown."""
import re
from dataclasses import dataclass, field

from .. import settings

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class AiError(Exception):
    """A provider failed or returned something unusable. `code` is safe to show; details never reach the learner."""

    def __init__(self, code="provider_error"):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class TutorRequest:
    mode: str                                   # 'child' | 'teen' | 'adult'
    language: str                               # the language being learned (name)
    cefr: str
    message: str                                # the learner's message, or the helper question's wording in child mode
    facts: tuple = ()                           # stored facts about this learner, already bounded: short strings
    history: tuple = ()                         # ((role, text), ...) the last few messages only
    context_title: str | None = None            # the lesson / situation / topic the conversation is about
    phrases: tuple = ()                         # phrases from the learner's available content: ({text, pronunciation, meaning}, ...)
    turn_index: int = 0                         # how many learner messages came before this one
    quick_prompt: str | None = None             # child mode: which helper question was chosen


@dataclass(frozen=True)
class RoleplayTurnRequest:
    mode: str
    language: str
    cefr: str
    situation: dict                             # {title, setting, goal, partner_name, partner_role}
    objective: str                              # what the learner is trying to do at this step (never the answer)
    learner_text: str
    verdict: str                                # 'correct' | 'incorrect' (decided by the server, not by the model)
    attempt_no: int
    hint: str | None                            # server-chosen hint after a wrong try
    revealed: str | None                        # the model answer, only once the step is correct or has been missed
    history: tuple = ()                         # ((speaker, text), ...) this session's last few turns
    weaknesses: tuple = ()                      # relevant weak phrases for this situation (strings)
    next_objective: str | None = None


@dataclass(frozen=True)
class RoleplayFeedbackRequest:
    mode: str
    language: str
    cefr: str
    situation: dict
    steps_total: int
    steps_correct: int
    steps_missed: int
    first_try_correct: int
    missed: tuple = ()                          # ({objective, answer}, ...) answers revealed during the session
    voice_turns: int = 0


@dataclass(frozen=True)
class SemanticGradeRequest:
    """Asks whether the learner's answer MEANS the same as an accepted answer. Carries the accepted answers (the grader needs them) and
    nothing about the learner. Never sent to a child's provider: children are always graded by the built-in grader."""
    language: str
    language_code: str
    cefr: str
    objective: str
    learner_text: str
    accepted: tuple                               # the stored accepted answers (server-side key)
    det_confidence: float                         # what the deterministic grader already found
    det_coverage: float


@dataclass(frozen=True)
class MicroLessonRequest:
    mode: str
    language: str
    cefr: str
    kind: str                                     # 'vocab_choice' | 'phrase_choice' | 'translation'
    item: dict                                    # the canonical item: {text, pronunciation, meaning}
    distractors: tuple = ()                       # other canonical phrases/meanings from the learner's own content
    difficulty: int = 1


@dataclass(frozen=True)
class InsightRewriteRequest:
    mode: str
    language: str
    kind: str
    base_text: str                                # the claim, already decided by the server from stored evidence
    evidence: tuple = ()                          # the evidence texts that support it


@dataclass(frozen=True)
class RankRequest:
    mode: str
    language: str
    cefr: str
    candidates: tuple                             # ({id, kind, title, reason, evidence: (text, ...)}, ...): all eligible, all decided by rules
    base_order: tuple                             # the ids in the deterministic order


FEEDBACK_FIELDS = ("vocabulary_feedback", "grammar_feedback", "hint", "encouragement", "next_step")


class Provider:
    name = "base"

    def tutor_reply(self, req: TutorRequest) -> str:
        raise NotImplementedError

    def roleplay_reply(self, req: RoleplayTurnRequest) -> str:
        raise NotImplementedError

    def roleplay_feedback(self, req: RoleplayFeedbackRequest) -> dict:
        raise NotImplementedError

    # --- Phase 12 capabilities. A provider that does not support one raises; callers fall back to the deterministic result. ---
    def semantic_grade(self, req: SemanticGradeRequest) -> dict:
        raise NotImplementedError

    def generate_micro_lesson(self, req: MicroLessonRequest) -> dict:
        raise NotImplementedError

    def rewrite_insight(self, req: InsightRewriteRequest) -> str:
        raise NotImplementedError

    def rank_recommendations(self, req: RankRequest) -> list:
        raise NotImplementedError


def clean(text, limit=None):
    """Plain, bounded text: control characters removed, trimmed, cut to the limit. Empty or non-text is a provider error."""
    if not isinstance(text, str):
        raise AiError("invalid_response")
    text = _CONTROL.sub("", text).strip()
    if not text:
        raise AiError("empty_response")
    limit = limit or settings.AI_MAX_REPLY_CHARS
    return text[:limit].rstrip()


def clean_feedback(data):
    if not isinstance(data, dict):
        raise AiError("invalid_response")
    return {k: clean(data.get(k), 400) for k in FEEDBACK_FIELDS}
