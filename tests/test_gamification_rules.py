"""The gamification rules as pure functions: level thresholds at their boundaries, ranks, and streak and freeze arithmetic."""
from datetime import date, timedelta

import pytest

from backend.gamification import rules, streaks

D0 = date(2026, 9, 1)


def d(n):
    return D0 + timedelta(days=n)


# ---------- levels ----------
@pytest.mark.parametrize("xp,level", [(-50, 1), (0, 1), (1, 1), (99, 1), (100, 2), (101, 2), (299, 2), (300, 3), (599, 3), (600, 4), (999, 4), (1000, 5),
                                      (1499, 5), (1500, 6), (2099, 6), (2100, 7), (10 ** 9, rules.MAX_LEVEL)])
def test_level_boundaries(xp, level):
    assert rules.level_for(xp) == level


def test_level_starts_are_defined_and_increasing():
    assert [rules.level_start(l) for l in range(1, 7)] == [0, 100, 300, 600, 1000, 1500]
    starts = [rules.level_start(l) for l in range(1, rules.MAX_LEVEL + 1)]
    assert starts == sorted(set(starts))


def test_every_level_starts_exactly_at_its_threshold():
    for l in range(1, rules.MAX_LEVEL + 1):
        assert rules.level_for(rules.level_start(l)) == l
        if l > 1:
            assert rules.level_for(rules.level_start(l) - 1) == l - 1


@pytest.mark.parametrize("level,name", [(1, "Explorer"), (2, "Explorer"), (3, "Traveller"), (4, "Traveller"), (5, "Local"), (7, "Local"), (8, "Insider"),
                                        (11, "Insider"), (12, "Native"), (20, "Native")])
def test_ranks(level, name):
    assert rules.rank_for(level) == name


def test_xp_rules_are_positive_and_bounded():
    assert set(rules.XP_RULES) == {"exercise", "lesson", "situation", "listening", "speaking", "daily_task"}
    assert all(0 < v <= 100 for v in rules.XP_RULES.values())
    assert rules.DAILY_XP_CAP >= max(rules.XP_RULES.values())


# ---------- streaks ----------
def run(days, used=(), earned=(), today=None):
    return streaks.compute([d(i) for i in days], [d(i) for i in used], [d(i) for i in earned], d(today if today is not None else max(days, default=0)))


def test_no_activity_no_streak():
    r = run([], today=5)
    assert (r.current, r.longest, r.active_today, r.at_risk) == (0, 0, False, False)


def test_one_day():
    r = run([3], today=3)
    assert (r.current, r.longest, r.active_today) == (1, 1, True)


def test_consecutive_days_count():
    assert run([0, 1, 2, 3]).current == 4


def test_repeating_a_day_does_not_inflate():
    assert run([0, 0, 0, 1, 1]).current == 2


def test_a_missed_day_breaks_the_streak_without_a_freeze():
    r = run([0, 1, 2, 4], today=4)
    assert r.current == 1 and r.longest == 3 and r.new_used == []


def test_alive_through_yesterday_and_flags_risk():
    r = run([0, 1, 2], today=3)
    assert r.current == 3 and r.at_risk is True and r.active_today is False


def test_stale_streak_is_zero_but_longest_remains():
    r = run([0, 1, 2], today=4)
    assert r.current == 0 and r.longest == 3 and r.at_risk is False


def test_a_freeze_protects_one_missed_day():
    r = run([0, 1, 2, 4], earned=[1], today=4)
    assert r.current == 4 and r.new_used == [d(3)]                 # 0, 1, 2, (3 frozen), 4


def test_a_protected_day_keeps_the_run_but_is_not_counted():
    r = run([0, 1, 2, 4], earned=[1], today=4)
    assert r.current == 4                                          # four ACTIVE days; the frozen day 3 is not one of them


def test_freeze_must_cover_the_whole_gap():
    r = run([0, 1, 4], earned=[1], today=4)                        # two missed days, one freeze
    assert r.current == 1 and r.new_used == []                     # streak restarts and the freeze is not spent


def test_two_freezes_cover_two_missed_days():
    r = run([0, 1, 4], earned=[0, 1], today=4)
    assert r.new_used == [d(2), d(3)] and r.current == 3


def test_an_already_used_freeze_is_honoured_and_not_used_again():
    r = run([0, 1, 2, 4], earned=[1], used=[3], today=4)
    assert r.new_used == [] and r.current == 4


def test_a_freeze_earned_later_cannot_cover_an_earlier_gap():
    r = run([0, 2, 3], earned=[3], today=3)                        # the freeze only exists from day 3 on
    assert r.new_used == [] and r.current == 2


def test_a_freeze_spent_earlier_is_not_available_again():
    r = run([0, 1, 3, 5], earned=[1], used=[2], today=5)           # one freeze, already spent on day 2; day 4 has none left
    assert r.new_used == [] and r.current == 1


def test_a_freeze_is_earned_on_the_seventh_day():
    r = run(list(range(7)))
    assert r.new_earned == [d(6)] and r.current == 7


def test_no_freeze_before_the_seventh_day():
    assert run(list(range(6))).new_earned == []


def test_earned_freeze_is_not_granted_twice():
    assert run(list(range(7)), earned=[6]).new_earned == []


def test_freezes_are_capped():
    r = run(list(range(21)), earned=[6, 13])                       # already holding two: the 21st day earns nothing
    assert r.new_earned == []
    r = run(list(range(14)))
    assert r.new_earned == [d(6), d(13)]


def test_cap_matches_the_rules_constant():
    assert rules.MAX_FREEZES == 2 and rules.FREEZE_EVERY == 7


def test_seventh_day_counts_only_active_days_not_frozen_ones():
    r = run([0, 1, 2, 4, 5, 6], earned=[1], today=6)               # 6 active days (day 3 frozen): not yet 7
    assert r.current == 6 and r.new_earned == []


def test_longest_survives_a_break():
    r = run([0, 1, 2, 3, 4, 10, 11], today=11)
    assert r.longest == 5 and r.current == 2


def test_freeze_after_a_break_cannot_resurrect_the_old_streak():
    r = run([0, 1, 2, 6, 7], earned=[2], today=7)                  # four missed days, one freeze
    assert r.current == 2 and r.new_used == []
