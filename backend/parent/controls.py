"""The one place that decides whether a learner may use voice features. Called by every speaking step that captures or analyses
audio. Two independent reasons say no, and nothing can say yes to what either refuses:
  * the product keeps voice off for the child age group (Phase 8), whatever any control says;
  * a linked parent has switched it off (Phase 9)."""
from ..personalization.context import Forbidden
from ..repositories import parent as repo


def voice_block_reason(conn, ctx, user_id):
    """None when voice is allowed, else 'age_group' or 'parent_control'."""
    if ctx["age_group_code"] == "child":
        return "age_group"
    if repo.voice_disabled_for_learner(conn, user_id):
        return "parent_control"
    return None


def require_voice(conn, ctx, user_id):
    if voice_block_reason(conn, ctx, user_id) is not None:
        raise Forbidden()
