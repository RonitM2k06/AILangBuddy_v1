"""Explicit response and request models for /api/admin/*. Responses are allow-lists: a database row is never returned directly, so a column added
later cannot leak by accident. Requests forbid unknown fields, and none of them can name an actor (the actor is the session)."""
from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuditMeta(BaseModel):
    revision_before: int | None = None
    revision_after: int | None = None
    changed_fields: list[str] | None = None
    finding_codes: list[str] | None = None
    status_before: str | None = None
    status_after: str | None = None


class AuditEventOut(BaseModel):
    id: int
    occurred_at: str
    actor: str
    action: str
    entity_type: str
    entity_id: int | None
    entity_key: str | None
    outcome: str
    meta: AuditMeta
    request_id: str | None


class AuditPageOut(BaseModel):
    items: list[AuditEventOut]
    total: int
    limit: int
    offset: int


class FindingOut(BaseModel):
    code: str
    severity: str
    entity: str
    message: str


class ValidateOut(BaseModel):
    ok: bool
    findings: list[FindingOut]


class SweepFindingOut(FindingOut):
    entity_status: str | None


class SweepOut(BaseModel):
    ok: bool
    checked: dict[str, int]
    errors: int
    warnings: int
    published_errors: int
    findings: list[SweepFindingOut]


# =====================================================================================================================
# CMS requests. Unknown fields are refused; none can name an actor; `revision` is the optimistic-concurrency token on every edit of a unit.
# =====================================================================================================================
from typing import Literal  # noqa: E402

from pydantic import Field  # noqa: E402

Slug = Field(max_length=60)
Short = Field(max_length=500)
Prose = Field(max_length=2000)
Title = Field(max_length=120)
Revision = Field(ge=1, le=10**9)
SortOrder = Field(default=None, ge=1, le=9999)


class AnswerIn(Strict):
    id: int | None = Field(default=None, ge=1)
    text: str = Field(max_length=400)
    is_correct: bool = True


class LessonCreate(Strict):
    slug: str = Slug
    language: str = Field(max_length=16)
    cefr: str = Field(max_length=4)
    title: str = Title
    description: str = Prose
    situation: str | None = Field(default=None, max_length=500)
    tip: str | None = Field(default=None, max_length=500)
    sort_order: int | None = SortOrder
    topics: list[str] = Field(default_factory=list, max_length=10)
    age_groups: list[str] = Field(default_factory=list, max_length=3)


class LessonPatch(Strict):
    revision: int = Revision
    slug: str = Field(default=None, max_length=60)
    cefr: str = Field(default=None, max_length=4)
    title: str = Field(default=None, max_length=120)
    description: str = Field(default=None, max_length=2000)
    situation: str | None = Field(default=None, max_length=500)
    tip: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=None, ge=1, le=9999)
    topics: list[str] = Field(default=None, max_length=10)
    age_groups: list[str] = Field(default=None, max_length=3)


class ExerciseCreate(Strict):
    revision: int = Revision
    kind: Literal["multiple_choice", "translation", "fill_blank"]
    prompt: str = Short
    explanation: str | None = Field(default=None, max_length=2000)
    item_id: int | None = Field(default=None, ge=1)
    difficulty: int = 1
    sort_order: int | None = SortOrder
    answers: list[AnswerIn] = Field(max_length=12)


class ExercisePatch(Strict):
    revision: int = Revision
    prompt: str = Field(default=None, max_length=500)
    explanation: str | None = Field(default=None, max_length=2000)
    item_id: int | None = Field(default=None, ge=1)
    difficulty: int = None
    sort_order: int | None = None
    answers: list[AnswerIn] = Field(default=None, max_length=12)


class VocabularyLinks(Strict):
    revision: int = Revision
    item_ids: list[int] = Field(max_length=200)


class SituationCreate(Strict):
    slug: str = Slug
    language: str = Field(max_length=16)
    cefr: str = Field(max_length=4)
    topic: str = Field(max_length=60)
    title: str = Title
    description: str = Prose
    goal: str | None = Field(default=None, max_length=500)
    setting: str | None = Field(default=None, max_length=500)
    partner_name: str | None = Field(default=None, max_length=60)
    partner_role: str | None = Field(default=None, max_length=60)
    difficulty: int = 1
    sort_order: int | None = SortOrder
    age_groups: list[str] = Field(default_factory=list, max_length=3)


class SituationPatch(Strict):
    revision: int = Revision
    slug: str = Field(default=None, max_length=60)
    cefr: str = Field(default=None, max_length=4)
    topic: str = Field(default=None, max_length=60)
    title: str = Field(default=None, max_length=120)
    description: str = Field(default=None, max_length=2000)
    goal: str | None = Field(default=None, max_length=500)
    setting: str | None = Field(default=None, max_length=500)
    partner_name: str | None = Field(default=None, max_length=60)
    partner_role: str | None = Field(default=None, max_length=60)
    difficulty: int = None
    sort_order: int = Field(default=None, ge=1, le=9999)
    age_groups: list[str] = Field(default=None, max_length=3)


class StepCreate(Strict):
    revision: int = Revision
    kind: Literal["learn_phrase", "choose_response", "translate", "fill_blank", "conversation"]
    prompt: str | None = Field(default=None, max_length=500)
    prompt_meaning: str | None = Field(default=None, max_length=500)
    item_id: int | None = Field(default=None, ge=1)
    explanation: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = SortOrder
    answers: list[AnswerIn] = Field(default_factory=list, max_length=12)


class StepPatch(Strict):
    revision: int = Revision
    prompt: str | None = Field(default=None, max_length=500)
    prompt_meaning: str | None = Field(default=None, max_length=500)
    item_id: int | None = Field(default=None, ge=1)
    explanation: str | None = Field(default=None, max_length=2000)
    sort_order: int | None = None
    answers: list[AnswerIn] = Field(default=None, max_length=12)


class ActivityCreate(Strict):
    slug: str = Slug
    language: str = Field(max_length=16)
    cefr: str = Field(max_length=4)
    topic: str = Field(max_length=60)
    item_id: int = Field(ge=1)
    title: str = Title
    mode: Literal["choose_meaning", "choose_phrase"]
    prompt: str = Prose
    difficulty: int = 1
    sort_order: int | None = SortOrder
    age_groups: list[str] = Field(default_factory=list, max_length=3)


class ActivityPatch(Strict):
    revision: int = Revision
    slug: str = Field(default=None, max_length=60)
    cefr: str = Field(default=None, max_length=4)
    topic: str = Field(default=None, max_length=60)
    item_id: int = Field(default=None, ge=1)
    title: str = Field(default=None, max_length=120)
    mode: Literal["choose_meaning", "choose_phrase"] = None
    prompt: str = Field(default=None, max_length=2000)
    difficulty: int = None
    sort_order: int = Field(default=None, ge=1, le=9999)
    age_groups: list[str] = Field(default=None, max_length=3)


class OptionCreate(Strict):
    revision: int = Revision
    item_id: int = Field(ge=1)
    sort_order: int | None = SortOrder


class OptionPatch(Strict):
    revision: int = Revision
    item_id: int = Field(default=None, ge=1)
    sort_order: int | None = None


class TranslationIn(Strict):
    language: str = Field(max_length=16)
    meaning: str = Field(max_length=400)
    natural: str | None = Field(default=None, max_length=400)


class TranslationPut(Strict):
    meaning: str = Field(max_length=400)
    natural: str | None = Field(default=None, max_length=400)


class VocabularyCreate(Strict):
    language: str = Field(max_length=16)
    cefr: str = Field(max_length=4)
    kind: Literal["word", "phrase"]
    text: str = Field(max_length=300)
    pronunciation: str | None = Field(default=None, max_length=300)
    translations: list[TranslationIn] = Field(default_factory=list, max_length=12)


class VocabularyPatch(Strict):
    cefr: str = Field(default=None, max_length=4)
    kind: Literal["word", "phrase"] = None
    text: str = Field(default=None, max_length=300)
    pronunciation: str | None = Field(default=None, max_length=300)


class TopicCreate(Strict):
    slug: str = Slug
    name: str = Field(max_length=100)
    icon: str = Field(max_length=40)


class TopicPatch(Strict):
    name: str = Field(default=None, max_length=100)
    icon: str = Field(default=None, max_length=40)


class Transition(Strict):
    revision: int = Revision


# =====================================================================================================================
# CMS responses (allow-lists)
# =====================================================================================================================
class LanguageRef(BaseModel):
    code: str
    name: str


class UnitSummary(BaseModel):
    id: int
    slug: str
    title: str
    language: str
    cefr: str
    status: str
    revision: int
    sort_order: int
    updated_at: str | None
    published_at: str | None
    archived_at: str | None


class LessonSummary(UnitSummary):
    exercises: int
    vocabulary: int


class SituationSummary(UnitSummary):
    steps: int


class ActivitySummary(UnitSummary):
    options: int


class LessonPageOut(BaseModel):
    items: list[LessonSummary]
    total: int
    limit: int
    offset: int


class SituationPageOut(BaseModel):
    items: list[SituationSummary]
    total: int
    limit: int
    offset: int


class ActivityPageOut(BaseModel):
    items: list[ActivitySummary]
    total: int
    limit: int
    offset: int


class AnswerOut(BaseModel):
    id: int
    text: str
    is_correct: bool
    sort_order: int


class ExerciseOut(BaseModel):
    id: int
    kind: str
    prompt: str
    explanation: str | None
    item_id: int | None
    difficulty: int
    sort_order: int
    answers: list[AnswerOut]


class TopicRef(BaseModel):
    slug: str
    name: str


class VocabLinkOut(BaseModel):
    item_id: int
    text: str
    meaning_en: str | None
    sort_order: int


class LessonOut(BaseModel):
    id: int
    slug: str
    language: LanguageRef
    cefr: str
    title: str
    description: str
    situation: str | None
    tip: str | None
    sort_order: int
    status: str
    revision: int
    published_at: str | None
    archived_at: str | None
    updated_at: str | None
    topics: list[TopicRef]
    age_groups: list[str]
    vocabulary: list[VocabLinkOut]
    exercises: list[ExerciseOut]


class ExerciseWriteOut(BaseModel):
    revision: int
    exercise: ExerciseOut


class StepOut(BaseModel):
    id: int
    sort_order: int
    kind: str
    prompt: str | None
    prompt_meaning: str | None
    item_id: int | None
    explanation: str | None
    answers: list[AnswerOut]


class SituationOut(BaseModel):
    id: int
    slug: str
    language: LanguageRef
    cefr: str
    title: str
    description: str
    goal: str | None
    setting: str | None
    partner_name: str | None
    partner_role: str | None
    difficulty: int
    topic: str | None
    sort_order: int
    status: str
    revision: int
    published_at: str | None
    archived_at: str | None
    updated_at: str | None
    age_groups: list[str]
    steps: list[StepOut]


class StepWriteOut(BaseModel):
    revision: int
    step: StepOut


class OptionOut(BaseModel):
    id: int
    item_id: int
    sort_order: int
    text: str | None
    meaning_en: str | None
    is_target: bool


class TargetOut(BaseModel):
    item_id: int
    text: str | None
    meaning_en: str | None


class ActivityOut(BaseModel):
    id: int
    slug: str
    language: LanguageRef
    cefr: str
    title: str
    mode: str
    prompt: str
    difficulty: int
    topic: str | None
    sort_order: int
    status: str
    revision: int
    published_at: str | None
    archived_at: str | None
    updated_at: str | None
    age_groups: list[str]
    target: TargetOut
    options: list[OptionOut]


class OptionWriteOut(BaseModel):
    revision: int
    option: OptionOut


class TranslationOut(BaseModel):
    language: str
    meaning: str
    natural: str | None


class VocabUsage(BaseModel):
    lessons: int
    situations: int
    listening_activities: int


class VocabularyOut(BaseModel):
    id: int
    language: str
    cefr: str
    kind: str
    text: str
    pronunciation: str | None
    translations: list[TranslationOut]
    usage: VocabUsage
    referenced: bool
    used_by_published: bool


class VocabularySummary(BaseModel):
    id: int
    language: str
    cefr: str
    kind: str
    text: str
    pronunciation: str | None
    has_english: bool


class VocabularyPageOut(BaseModel):
    items: list[VocabularySummary]
    total: int
    limit: int
    offset: int


class TopicOut(BaseModel):
    id: int
    slug: str
    name: str
    icon: str
    lessons: int
    situations: int
    listening_activities: int


class TopicsOut(BaseModel):
    items: list[TopicOut]


class ReferenceLanguage(BaseModel):
    code: str
    name: str
    native_name: str
    cefr_levels: list[str]


class ReferenceCefr(BaseModel):
    code: str
    rank: int
    label: str


class ReferenceAge(BaseModel):
    code: str
    label: str
    min_age: int
    max_age: int | None


class ReferenceOut(BaseModel):
    languages: list[ReferenceLanguage]
    cefr_levels: list[ReferenceCefr]
    age_groups: list[ReferenceAge]


class LanguagesOut(BaseModel):
    items: list[ReferenceLanguage]


class CefrLevelsOut(BaseModel):
    items: list[ReferenceCefr]


class AgeGroupsOut(BaseModel):
    items: list[ReferenceAge]


class LifecycleOut(BaseModel):
    entity_type: str
    id: int
    status: str
    revision: int
    published_at: str | None
    archived_at: str | None
    warnings: list[FindingOut]


# =====================================================================================================================
# Analytics responses. Every figure is a CountMetric / RateMetric / Bucket: a value (or None) plus a status of ok | no_data | suppressed.
# =====================================================================================================================
from typing import Any  # noqa: E402


class CountMetric(BaseModel):
    value: int | None
    status: str


class RateMetric(BaseModel):
    numerator: int | None
    denominator: int | None
    rate: float | None
    status: str


class Bucket(BaseModel):
    key: str
    label: str
    count: int | None
    learners: int | None
    status: str


class Distribution(BaseModel):
    total: CountMetric
    buckets: list[Bucket]


class WindowOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: str = Field(alias="from")
    to: str
    days: int


class Meta(BaseModel):
    generated_at: str
    timezone: str
    window: WindowOut


class ActivityHeadline(BaseModel):
    as_of: str
    dau: CountMetric
    wau: CountMetric
    mau: CountMetric


class LearnersBlock(BaseModel):
    total: CountMetric
    new: CountMetric
    active: CountMetric


class Distributions(BaseModel):
    language: Distribution
    cefr: Distribution
    age_group: Distribution


class LearningBlock(BaseModel):
    lesson_completion: RateMetric
    exercise_accuracy: RateMetric
    situation_completion: RateMetric
    listening_accuracy: RateMetric


class PronunciationUsage(BaseModel):
    attempts: CountMetric
    learners: CountMetric


class RoleplayBlock(BaseModel):
    started: CountMetric
    completed: CountMetric
    success: RateMetric


class SpeakingBlock(BaseModel):
    speaking_participation: RateMetric
    pronunciation_usage: PronunciationUsage
    roleplay: RoleplayBlock


class XpBlock(BaseModel):
    events: CountMetric
    xp_awarded: CountMetric
    learners_earning: CountMetric


class StreakBlock(BaseModel):
    streak_days: CountMetric
    learners: CountMetric


class AchievementsBlock(BaseModel):
    unlocks: CountMetric
    learners: CountMetric
    by_achievement: list[Bucket]


class ChallengesBlock(BaseModel):
    started: CountMetric
    claim_rate: RateMetric


class EngagementBlock(BaseModel):
    xp: XpBlock
    streak: StreakBlock
    achievements: AchievementsBlock
    challenges: ChallengesBlock


class RecommendationsBlock(BaseModel):
    shown: CountMetric
    learners: CountMetric
    applied_rate: RateMetric


class MicroLessonsBlock(BaseModel):
    generated: CountMetric
    attempted: CountMetric
    attempts: CountMetric
    attempt_accuracy: RateMetric


class AdaptiveBlock(BaseModel):
    recommendations: RecommendationsBlock
    micro_lessons: MicroLessonsBlock


class DashboardOut(Meta):
    window_name: str
    learners: LearnersBlock
    activity: ActivityHeadline
    distributions: Distributions
    learning: LearningBlock
    speaking: SpeakingBlock
    engagement: EngagementBlock
    adaptive: AdaptiveBlock


class ActivityPoint(BaseModel):
    date: str
    days: int | None = None
    dau: CountMetric | None = None
    wau: CountMetric | None = None
    mau: CountMetric | None = None
    active_learners: CountMetric | None = None


class ActivitySeriesOut(Meta):
    grain: str
    points: list[ActivityPoint]
    evidence_kinds: list[str]


class LearningOut(Meta, LearningBlock):
    pass


class SpeakingOut(Meta, SpeakingBlock):
    pass


class ConfidencePoint(BaseModel):
    topic: TopicRef
    learners: int | None
    mean_confidence: float | None
    mean_accuracy: float | None
    gap: float | None
    status: str


class RuleBucket(BaseModel):
    rule: str
    weaknesses: int | None
    learners: int | None
    status: str


class WeaknessBlock(BaseModel):
    as_of: str
    by_rule: list[RuleBucket]
    by_topic: list[Bucket]


class ConfidenceWeaknessOut(Meta):
    confidence_vs_performance: list[ConfidencePoint]
    weaknesses: WeaknessBlock


class EngagementOut(Meta, EngagementBlock):
    pass


class AdaptiveOut(Meta, AdaptiveBlock):
    pass


class ContentPerformanceItem(BaseModel):
    id: int
    slug: str
    title: str
    status: str
    cell: str
    attempts: int | None
    learners: int | None
    accuracy: float | None
    completion: RateMetric | None
    review_candidate: bool


class ContentPerformanceOut(Meta):
    kind: str
    items: list[ContentPerformanceItem]
    total: int
    limit: int
    offset: int


# ---------- learner overview and health ----------
class LearnerRow(BaseModel):
    ref: str
    language: str | None
    cefr: str | None
    age_group: str | None
    joined: str
    last_active: str | None
    lessons_completed: int
    situations_completed: int
    exercise_attempts: int


class LearnerPageOut(BaseModel):
    suppressed: bool
    total: int | None
    items: list[LearnerRow]
    limit: int
    offset: int


class LearnerTotals(BaseModel):
    lessons_started: int
    lessons_completed: int
    situations_started: int
    situations_completed: int
    exercise_attempts: int
    exercise_correct: int
    listening_attempts: int
    listening_correct: int
    speaking_attempts: int
    roleplay_sessions_started: int
    roleplay_sessions_completed: int
    xp_total: int
    achievements_unlocked: int
    active_days_30: int


class LearnerOut(BaseModel):
    suppressed: bool
    ref: str
    language: str | None = None
    cefr: str | None = None
    age_group: str | None = None
    joined: str | None = None
    last_active: str | None = None
    totals: LearnerTotals | None = None


class MigrationOut(BaseModel):
    version: str
    name: str
    applied_at: str


class DatabaseOut(BaseModel):
    integrity: str
    foreign_keys: str


class StatusCounts(BaseModel):
    draft: int
    published: int
    archived: int


class ContentCounts(BaseModel):
    lessons: StatusCounts
    situations: StatusCounts
    listening_activities: StatusCounts


class ProvidersOut(BaseModel):
    llm_configured: bool
    speech_to_text_configured: bool
    pronunciation_configured: bool
    tutor_uses_llm: bool


class SecurityWarningOut(BaseModel):
    code: str
    severity: Literal["critical", "warning"]
    message: str


class SecurityHealthOut(BaseModel):
    cookie_secure: bool
    totp_key: Literal["valid", "missing", "malformed"]
    demo_mode: bool
    demo_live_ai: bool
    admins: int
    admins_with_two_factor: int
    warnings: list[SecurityWarningOut]


class HealthOut(BaseModel):
    app_version: str
    last_migration: MigrationOut
    database: DatabaseOut
    content: ContentCounts
    demo_mode: bool
    providers: ProvidersOut
    security: SecurityHealthOut


# ---------- Phase 14E: accounts and security events ----------
class AccountOut(BaseModel):
    ref: str
    roles: list[str]
    created: str
    two_factor: bool


class AccountPageOut(BaseModel):
    items: list[AccountOut]
    total: int
    limit: int
    offset: int


class SecurityEventOut(BaseModel):
    occurred_at: str
    type: str
    outcome: str
    account: str | None
    method: str | None
    reason: str | None
    stage: str | None
    count: int | None
    network: str | None


class SecurityEventPageOut(BaseModel):
    items: list[SecurityEventOut]
    limit: int
    next: str | None
