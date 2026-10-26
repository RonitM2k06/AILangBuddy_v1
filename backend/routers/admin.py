"""The Phase 13 admin API: one router, mounted once, every route behind admin_only and csrf_guard. Route handlers only translate HTTP: the rules
live in backend/admin/*, the SQL in backend/repositories/*. (GET /api/admin/users, once a Phase 2 route elsewhere, is here since Phase 14E.)"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from ..admin import analytics, audit, cms, cms_listening, cms_situations, cms_vocabulary, errors, lifecycle, schemas, validation
from ..admin import health as health_service
from ..admin import security_views
from ..auth import events as auth_events
from ..admin import learners as learners_service
from ..admin.security import admin_only, csrf_guard, request_id
from ..auth.deps import db_path

router = APIRouter(prefix="/api/admin", dependencies=[Depends(admin_only), Depends(csrf_guard)])

TIME = r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$"
EntityType = Literal["lesson", "situation", "listening_activity"]


def _guard(fn, *args, **kwargs):
    """Domain errors -> HTTP. The services raise; nothing below this line knows about HTTP."""
    try:
        return fn(*args, **kwargs)
    except errors.NotFound:
        raise HTTPException(status_code=404, detail="Not found")
    except errors.InvalidInput as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", exc.field], "msg": exc.message, "type": "value_error"}])
    except errors.Conflict as exc:
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": exc.message, **exc.extra})
    except errors.ValidationFailed as exc:
        raise HTTPException(status_code=422, detail={"code": "validation_failed", "message": "Publication blocked: the content has errors.", "findings": exc.findings})


# ---------- validation ----------
@router.get("/validate/all", response_model=schemas.SweepOut)
def validate_all(path=Depends(db_path)):
    """The integrity sweep: every lesson, situation and listening activity plus whole-database checks. Writes nothing."""
    return validation.sweep(path)


@router.post("/validate/{entity_type}/{entity_id}", response_model=schemas.ValidateOut)
def validate_one(entity_type: EntityType, entity_id: int, path=Depends(db_path)):
    """A dry run of exactly the rules a publish applies. Writes nothing (and is not audited: it changes nothing)."""
    return _guard(validation.dry_run, path, entity_type, entity_id)


# ---------- audit ----------
@router.get("/audit", response_model=schemas.AuditPageOut)
def audit_list(actor: str | None = Query(default=None, max_length=64), entity_type: Literal[audit.ENTITY_TYPES] | None = None,
               entity_id: int | None = Query(default=None, ge=1), action: Literal[audit.ACTIONS] | None = None,
               outcome: Literal["ok", "rejected"] | None = None, from_: str | None = Query(default=None, alias="from", pattern=TIME),
               to: str | None = Query(default=None, pattern=TIME), limit: int = Query(default=25, ge=1, le=100), offset: int = Query(default=0, ge=0),
               path=Depends(db_path)):
    """Reading the log never writes to it."""
    filters = {"actor": actor, "entity_type": entity_type, "entity_id": entity_id, "action": action, "outcome": outcome, "from": from_, "to": to}
    total, items = audit.list_events(path, filters, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/audit/{event_id}", response_model=schemas.AuditEventOut)
def audit_get(event_id: int, path=Depends(db_path)):
    event = audit.get_event(path, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Not found")
    return event


# =====================================================================================================================
# content (a strict whitelist: lessons + exercises + vocabulary links, situations + steps, listening + options, vocabulary + translations, topics)
# There is no DELETE route anywhere. Every write needs the CSRF headers (router dependency) and, on a unit, the current `revision`.
# =====================================================================================================================
Status = Literal["draft", "published", "archived"]
Limit = Query(default=25, ge=1, le=100)
Offset = Query(default=0, ge=0)


def _page(total_items, limit, offset):
    total, items = total_items
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------- lessons ----------
@router.get("/content/lessons", response_model=schemas.LessonPageOut)
def lessons_list(status: Status | None = None, language: str | None = Query(default=None, max_length=16), cefr: str | None = Query(default=None, max_length=4),
                 q: str | None = Query(default=None, max_length=100), limit: int = Limit, offset: int = Offset, path=Depends(db_path)):
    return _page(cms.list_lessons(path, status, language, cefr, q, limit, offset), limit, offset)


@router.get("/content/lessons/{lesson_id}", response_model=schemas.LessonOut)
def lessons_get(lesson_id: int, path=Depends(db_path)):
    return _guard(cms.get_lesson, path, lesson_id)


@router.post("/content/lessons", response_model=schemas.LessonOut, status_code=201)
def lessons_create(body: schemas.LessonCreate, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms.create_lesson, path, user, rid, body)


@router.patch("/content/lessons/{lesson_id}", response_model=schemas.LessonOut)
def lessons_update(lesson_id: int, body: schemas.LessonPatch, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms.update_lesson, path, user, rid, lesson_id, body)


@router.post("/content/lessons/{lesson_id}/exercises", response_model=schemas.ExerciseWriteOut, status_code=201)
def exercises_create(lesson_id: int, body: schemas.ExerciseCreate, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms.create_exercise, path, user, rid, lesson_id, body)


@router.patch("/content/lessons/{lesson_id}/exercises/{exercise_id}", response_model=schemas.ExerciseWriteOut)
def exercises_update(lesson_id: int, exercise_id: int, body: schemas.ExercisePatch, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms.update_exercise, path, user, rid, lesson_id, exercise_id, body)


@router.put("/content/lessons/{lesson_id}/vocabulary", response_model=schemas.LessonOut)
def lesson_vocabulary_put(lesson_id: int, body: schemas.VocabularyLinks, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms.set_lesson_vocabulary, path, user, rid, lesson_id, body)


# ---------- situations ----------
@router.get("/content/situations", response_model=schemas.SituationPageOut)
def situations_list(status: Status | None = None, language: str | None = Query(default=None, max_length=16), cefr: str | None = Query(default=None, max_length=4),
                    q: str | None = Query(default=None, max_length=100), limit: int = Limit, offset: int = Offset, path=Depends(db_path)):
    return _page(cms_situations.list_situations(path, status, language, cefr, q, limit, offset), limit, offset)


@router.get("/content/situations/{situation_id}", response_model=schemas.SituationOut)
def situations_get(situation_id: int, path=Depends(db_path)):
    return _guard(cms_situations.get_situation, path, situation_id)


@router.post("/content/situations", response_model=schemas.SituationOut, status_code=201)
def situations_create(body: schemas.SituationCreate, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_situations.create_situation, path, user, rid, body)


@router.patch("/content/situations/{situation_id}", response_model=schemas.SituationOut)
def situations_update(situation_id: int, body: schemas.SituationPatch, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_situations.update_situation, path, user, rid, situation_id, body)


@router.post("/content/situations/{situation_id}/steps", response_model=schemas.StepWriteOut, status_code=201)
def steps_create(situation_id: int, body: schemas.StepCreate, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_situations.create_step, path, user, rid, situation_id, body)


@router.patch("/content/situations/{situation_id}/steps/{step_id}", response_model=schemas.StepWriteOut)
def steps_update(situation_id: int, step_id: int, body: schemas.StepPatch, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_situations.update_step, path, user, rid, situation_id, step_id, body)


# ---------- listening ----------
@router.get("/content/listening", response_model=schemas.ActivityPageOut)
def listening_list(status: Status | None = None, language: str | None = Query(default=None, max_length=16), cefr: str | None = Query(default=None, max_length=4),
                   q: str | None = Query(default=None, max_length=100), limit: int = Limit, offset: int = Offset, path=Depends(db_path)):
    return _page(cms_listening.list_activities(path, status, language, cefr, q, limit, offset), limit, offset)


@router.get("/content/listening/{activity_id}", response_model=schemas.ActivityOut)
def listening_get(activity_id: int, path=Depends(db_path)):
    return _guard(cms_listening.get_activity, path, activity_id)


@router.post("/content/listening", response_model=schemas.ActivityOut, status_code=201)
def listening_create(body: schemas.ActivityCreate, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_listening.create_activity, path, user, rid, body)


@router.patch("/content/listening/{activity_id}", response_model=schemas.ActivityOut)
def listening_update(activity_id: int, body: schemas.ActivityPatch, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_listening.update_activity, path, user, rid, activity_id, body)


@router.post("/content/listening/{activity_id}/options", response_model=schemas.OptionWriteOut, status_code=201)
def options_create(activity_id: int, body: schemas.OptionCreate, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_listening.create_option, path, user, rid, activity_id, body)


@router.patch("/content/listening/{activity_id}/options/{option_id}", response_model=schemas.OptionWriteOut)
def options_update(activity_id: int, option_id: int, body: schemas.OptionPatch, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_listening.update_option, path, user, rid, activity_id, option_id, body)


# ---------- vocabulary and translations ----------
@router.get("/content/vocabulary", response_model=schemas.VocabularyPageOut)
def vocabulary_list(language: str | None = Query(default=None, max_length=16), cefr: str | None = Query(default=None, max_length=4), kind: Literal["word", "phrase"] | None = None,
                    q: str | None = Query(default=None, max_length=100), limit: int = Limit, offset: int = Offset, path=Depends(db_path)):
    return _page(cms_vocabulary.list_vocabulary(path, language, cefr, kind, q, limit, offset), limit, offset)


@router.get("/content/vocabulary/{item_id}", response_model=schemas.VocabularyOut)
def vocabulary_get(item_id: int, path=Depends(db_path)):
    return _guard(cms_vocabulary.get_vocabulary, path, item_id)


@router.post("/content/vocabulary", response_model=schemas.VocabularyOut, status_code=201)
def vocabulary_create(body: schemas.VocabularyCreate, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_vocabulary.create_vocabulary, path, user, rid, body)


@router.patch("/content/vocabulary/{item_id}", response_model=schemas.VocabularyOut)
def vocabulary_update(item_id: int, body: schemas.VocabularyPatch, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_vocabulary.update_vocabulary, path, user, rid, item_id, body)


@router.put("/content/vocabulary/{item_id}/translations/{language_code}", response_model=schemas.VocabularyOut)
def translation_put(item_id: int, language_code: str, body: schemas.TranslationPut, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_vocabulary.put_translation, path, user, rid, item_id, language_code, body)


# ---------- topics ----------
@router.get("/content/topics", response_model=schemas.TopicsOut)
def topics_list(path=Depends(db_path)):
    return {"items": cms_vocabulary.list_topics(path)}


@router.post("/content/topics", response_model=schemas.TopicOut, status_code=201)
def topics_create(body: schemas.TopicCreate, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_vocabulary.create_topic, path, user, rid, body)


@router.patch("/content/topics/{topic_id}", response_model=schemas.TopicOut)
def topics_update(topic_id: int, body: schemas.TopicPatch, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _guard(cms_vocabulary.update_topic, path, user, rid, topic_id, body)


# ---------- reference data (read-only) ----------
@router.get("/content/languages", response_model=schemas.LanguagesOut)
def reference_languages(path=Depends(db_path)):
    return {"items": cms_vocabulary.reference(path)["languages"]}


@router.get("/content/cefr-levels", response_model=schemas.CefrLevelsOut)
def reference_cefr_levels(path=Depends(db_path)):
    return {"items": cms_vocabulary.reference(path)["cefr_levels"]}


@router.get("/content/age-groups", response_model=schemas.AgeGroupsOut)
def reference_age_groups(path=Depends(db_path)):
    return {"items": cms_vocabulary.reference(path)["age_groups"]}


# =====================================================================================================================
# publishing: the lifecycle. There is no DELETE: content is archived, never removed.
# =====================================================================================================================
def _transition(action, entity_type, entity_id, body, user, rid, path):
    return _guard(lifecycle.transition, path, user, rid, action, entity_type, entity_id, body.revision)


@router.post("/publish/{entity_type}/{entity_id}", response_model=schemas.LifecycleOut)
def publish(entity_type: EntityType, entity_id: int, body: schemas.Transition, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    """draft -> published, only if validation passes (422 with the findings otherwise; the refusal is audited)."""
    return _transition("publish", entity_type, entity_id, body, user, rid, path)


@router.post("/unpublish/{entity_type}/{entity_id}", response_model=schemas.LifecycleOut)
def unpublish(entity_type: EntityType, entity_id: int, body: schemas.Transition, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _transition("unpublish", entity_type, entity_id, body, user, rid, path)


@router.post("/archive/{entity_type}/{entity_id}", response_model=schemas.LifecycleOut)
def archive(entity_type: EntityType, entity_id: int, body: schemas.Transition, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _transition("archive", entity_type, entity_id, body, user, rid, path)


@router.post("/restore/{entity_type}/{entity_id}", response_model=schemas.LifecycleOut)
def restore(entity_type: EntityType, entity_id: int, body: schemas.Transition, user=Depends(admin_only), rid=Depends(request_id), path=Depends(db_path)):
    return _transition("restore", entity_type, entity_id, body, user, rid, path)


# =====================================================================================================================
# analytics: aggregates only, UTC, at most 365 days, small cells suppressed. Nothing here names a learner.
# =====================================================================================================================
DATE = r"^\d{4}-\d{2}-\d{2}$"
WindowName = Literal["7d", "30d", "90d"]


@router.get("/dashboard", response_model=schemas.DashboardOut, response_model_by_alias=True)
def dashboard(window: WindowName = "30d", path=Depends(db_path)):
    return _guard(analytics.dashboard, path, window)


@router.get("/analytics/activity", response_model=schemas.ActivitySeriesOut)
def analytics_activity(from_: str | None = Query(default=None, alias="from", pattern=DATE), to: str | None = Query(default=None, pattern=DATE),
                       window: WindowName | None = None, grain: Literal["day", "week"] = "day", path=Depends(db_path)):
    return _guard(analytics.activity_series, path, window, from_, to, grain)


def _windowed(fn, from_, to, window, path, *extra):
    return _guard(fn, path, *extra, window, from_, to)


@router.get("/analytics/learning", response_model=schemas.LearningOut)
def analytics_learning(from_: str | None = Query(default=None, alias="from", pattern=DATE), to: str | None = Query(default=None, pattern=DATE),
                       window: WindowName | None = None, path=Depends(db_path)):
    return _windowed(analytics.learning, from_, to, window, path)


@router.get("/analytics/speaking", response_model=schemas.SpeakingOut)
def analytics_speaking(from_: str | None = Query(default=None, alias="from", pattern=DATE), to: str | None = Query(default=None, pattern=DATE),
                       window: WindowName | None = None, path=Depends(db_path)):
    return _windowed(analytics.speaking, from_, to, window, path)


@router.get("/analytics/confidence-weakness", response_model=schemas.ConfidenceWeaknessOut)
def analytics_confidence_weakness(from_: str | None = Query(default=None, alias="from", pattern=DATE), to: str | None = Query(default=None, pattern=DATE),
                                  window: WindowName | None = None, path=Depends(db_path)):
    return _windowed(analytics.confidence_weakness, from_, to, window, path)


@router.get("/analytics/engagement", response_model=schemas.EngagementOut)
def analytics_engagement(from_: str | None = Query(default=None, alias="from", pattern=DATE), to: str | None = Query(default=None, pattern=DATE),
                         window: WindowName | None = None, path=Depends(db_path)):
    return _windowed(analytics.engagement, from_, to, window, path)


@router.get("/analytics/adaptive", response_model=schemas.AdaptiveOut)
def analytics_adaptive(from_: str | None = Query(default=None, alias="from", pattern=DATE), to: str | None = Query(default=None, pattern=DATE),
                       window: WindowName | None = None, path=Depends(db_path)):
    return _windowed(analytics.adaptive, from_, to, window, path)


@router.get("/analytics/content-performance", response_model=schemas.ContentPerformanceOut)
def analytics_content_performance(kind: Literal["lesson", "situation", "listening"] = "lesson", from_: str | None = Query(default=None, alias="from", pattern=DATE),
                                  to: str | None = Query(default=None, pattern=DATE), window: WindowName | None = None, limit: int = Query(default=50, ge=1, le=100),
                                  offset: int = Offset, path=Depends(db_path)):
    return _guard(analytics.content_performance, path, kind, window, from_, to, limit, offset)


# =====================================================================================================================
# learner overview (aggregate, opaque references, no impersonation) and health
# =====================================================================================================================
@router.get("/learners", response_model=schemas.LearnerPageOut)
def learners_list(language: str | None = Query(default=None, max_length=16), cefr: str | None = Query(default=None, max_length=4),
                  age_group: Literal["child", "teen", "adult"] | None = None, active_since: str | None = Query(default=None, pattern=DATE), limit: int = Limit, offset: int = Offset,
                  path=Depends(db_path)):
    return _guard(learners_service.list_learners, path, language, cefr, age_group, active_since, limit, offset)


@router.get("/learners/{ref}", response_model=schemas.LearnerOut)
def learners_get(ref: str = Path(pattern=r"^[0-9a-f]{32}$"), path=Depends(db_path)):
    return _guard(learners_service.get_learner, path, ref)


# =====================================================================================================================
# accounts and security events (Phase 14E): opaque references, closed fields, bounded pages; no filter by person
# =====================================================================================================================
@router.get("/users", response_model=schemas.AccountPageOut)
def accounts(limit: int = Query(default=25, ge=1, le=security_views.MAX_PAGE), offset: int = Query(default=0, ge=0, le=10_000_000), path=Depends(db_path)):
    """Every account as a reference, its roles, creation date and two-factor status. No e-mail, name, handle or anything secret."""
    return security_views.accounts(path, limit, offset)


@router.get("/security-events", response_model=schemas.SecurityEventPageOut)
def security_events(limit: int = Query(default=25, ge=1, le=security_views.MAX_PAGE), before: int | None = Query(default=None, ge=1, le=2**62),
                    type: Literal[tuple(sorted(auth_events.EVENT_TYPES))] | None = None, path=Depends(db_path)):
    """Newest first. `before` is the `next` cursor of the previous page. Reading the events records nothing."""
    return security_views.security_events(path, limit, before, type)


@router.get("/health", response_model=schemas.HealthOut)
def health(path=Depends(db_path)):
    return health_service.health(path)


@router.get("/health/integrity", response_model=schemas.SweepOut)
def health_integrity(path=Depends(db_path)):
    """The same sweep as GET /validate/all: lifecycle state, curriculum invariants, dangling references, orphans, incomplete content."""
    return validation.sweep(path)
