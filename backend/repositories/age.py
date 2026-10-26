"""One SQL fragment for age targeting, shared by every query that selects content for a learner.

A content row is visible to an age group if it has NO target rows (open to everyone) or one of its target rows names that
group. The fragment holds a single parameter for the age group id: positional ("?") by default, or named (":age")."""


def _open(table, fk, alias_id, param):
    return (f"(NOT EXISTS (SELECT 1 FROM {table} x WHERE x.{fk} = {alias_id}) "
            f"OR {alias_id} IN (SELECT {fk} FROM {table} WHERE age_group_id = {param}))")


def lesson(alias_id="l.id", param="?"):
    return _open("lesson_age_groups", "lesson_id", alias_id, param)


def situation(alias_id="s.id", param="?"):
    return _open("situation_age_groups", "situation_id", alias_id, param)


def listening(alias_id="a.id", param="?"):
    return _open("listening_activity_age_groups", "activity_id", alias_id, param)
