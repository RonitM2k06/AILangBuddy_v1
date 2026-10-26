"""The closed vocabularies the admin layer is allowed to log and report: validator finding codes (with their severity) and CMS field names.
The audit log accepts nothing outside these lists, so free text (an answer, a message, a secret) can never be written into an audit event."""

# code -> severity. 'error' blocks publication; 'warning' is shown and does not.
FINDING_CODES = {
    # lessons
    "lesson_no_exercises": "error", "lesson_no_topics": "error", "lesson_no_vocabulary": "error", "lesson_duplicate_title": "warning",
    # exercises
    "exercise_mc_too_few_answers": "error", "exercise_mc_correct_count": "error", "exercise_typed_no_accepted_answer": "error",
    "exercise_typed_incorrect_row": "error", "exercise_duplicate_answers": "error", "exercise_duplicate_prompt": "error",
    "exercise_invalid_difficulty": "error", "exercise_item_missing": "warning", "exercise_item_not_in_lesson": "warning",
    # situations
    "situation_no_steps": "error", "situation_topic_missing": "error", "situation_duplicate_title": "warning", "situation_invalid_difficulty": "error",
    "step_choose_too_few_answers": "error", "step_choose_correct_count": "error", "step_typed_no_accepted_answer": "error",
    "step_typed_incorrect_row": "error", "step_duplicate_answers": "error",
    # listening
    "listening_option_count": "error", "listening_target_not_in_options": "error", "listening_duplicate_option_text": "error",
    "listening_topic_missing": "error", "listening_invalid_difficulty": "error", "listening_duplicate_title": "warning",
    # shared
    "slug_invalid": "error", "text_control_characters": "error", "language_level_invalid": "error",
    "age_group_unknown": "error", "age_group_duplicate": "error",
    "vocabulary_missing_english": "error", "vocabulary_cefr_above_unit": "error", "vocabulary_unknown": "error",
    "dependency_unpublished": "error",
    "lifecycle_archived_without_time": "error", "lifecycle_time_without_archive": "error",
    "lifecycle_published_without_time": "warning",
    # integrity sweep (whole-database checks)
    "integrity_foreign_key": "error", "integrity_orphan_vocabulary": "warning", "integrity_orphan_topic": "warning",
    "integrity_database": "error",
}

# Names of the fields an admin can change, as they appear in the API (never values).
FIELD_NAMES = frozenset({
    "slug", "language", "cefr", "title", "description", "situation", "tip", "sort_order", "topics", "age_groups", "kind", "prompt", "prompt_meaning",
    "explanation", "difficulty", "item", "grammar_topic", "answers", "goal", "setting", "partner_name", "partner_role", "topic", "mode", "text",
    "pronunciation", "meaning", "natural", "name", "icon", "vocabulary", "options", "status",
})
