"""Phase 13F: the pure analytics rules: windows, small-cell suppression, rates and bucket folding. No database."""
from datetime import date, datetime, timezone

import pytest

from backend import settings
from backend.admin import analytics
from backend.admin.analytics import counted, distribution, fold_buckets, people, rate, resolve_window
from backend.admin.errors import InvalidInput


@pytest.fixture
def today(monkeypatch):
    monkeypatch.setattr(analytics, "utcnow", lambda: datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc))
    return date(2026, 3, 15)


# ---------- the constants the design fixes ----------
def test_the_fixed_design_constants():
    assert settings.SMALL_CELL == 5 and settings.ANALYTICS_MAX_WINDOW_DAYS == 365 and settings.ANALYTICS_WINDOWS == {"7d": 7, "30d": 30, "90d": 90}
    assert settings.REQUIRED_TRANSLATION_LANGUAGE == "en" and settings.LISTENING_OPTION_COUNT == 3


# ---------- windows ----------
@pytest.mark.parametrize("name,days,first", [("7d", 7, "2026-03-09"), ("30d", 30, "2026-02-14"), ("90d", 90, "2025-12-16")])
def test_named_windows_are_the_last_n_utc_days_ending_today_inclusive(today, name, days, first):
    w = resolve_window(window=name)
    assert (w["days"], w["from"].isoformat(), w["to"].isoformat()) == (days, first, "2026-03-15")
    assert w["start"] == f"{first} 00:00:00" and w["end"] == "2026-03-16 00:00:00"


def test_the_default_window_is_30_days(today):
    assert resolve_window()["days"] == 30 and resolve_window(default="7d")["days"] == 7


def test_explicit_dates_are_inclusive_and_end_exclusive_at_the_next_midnight(today):
    w = resolve_window(from_="2026-01-01", to="2026-01-31")
    assert (w["days"], w["start"], w["end"]) == (31, "2026-01-01 00:00:00", "2026-02-01 00:00:00")
    assert resolve_window(from_="2026-03-15", to="2026-03-15")["days"] == 1


def test_a_missing_end_means_today_and_a_missing_start_means_30_days_before_the_end(today):
    assert resolve_window(from_="2026-03-01")["to"] == today and resolve_window(to="2026-03-10")["from"].isoformat() == "2026-02-09"


def test_the_longest_window_is_365_days_and_not_366(today):
    assert resolve_window(from_="2025-03-16", to="2026-03-15")["days"] == 365
    with pytest.raises(InvalidInput):
        resolve_window(from_="2025-03-15", to="2026-03-15")


@pytest.mark.parametrize("kwargs", [{"window": "1y"}, {"window": "7d", "from_": "2026-03-01"}, {"window": "7d", "to": "2026-03-01"}, {"from_": "2026-03-10", "to": "2026-03-01"},
                                    {"from_": "2026-13-01"}, {"from_": "nonsense"}, {"to": "2026-02-30"}, {"from_": "2020-01-01", "to": "2026-03-15"}])
def test_unusable_windows_are_refused(today, kwargs):
    with pytest.raises(InvalidInput):
        resolve_window(**kwargs)


def test_the_window_boundaries_are_midnight_utc(today):
    w = resolve_window(from_="2026-02-14", to="2026-03-15")
    assert "2026-02-14 00:00:00" >= w["start"] and "2026-02-13 23:59:59" < w["start"]
    assert "2026-03-15 23:59:59" < w["end"] and "2026-03-16 00:00:00" >= w["end"]


# ---------- counts ----------
@pytest.mark.parametrize("n,expected", [(0, {"value": 0, "status": "ok"}), (1, {"value": None, "status": "suppressed"}), (4, {"value": None, "status": "suppressed"}),
                                        (5, {"value": 5, "status": "ok"}), (6, {"value": 6, "status": "ok"}), (1000, {"value": 1000, "status": "ok"})])
def test_a_count_of_learners_is_suppressed_from_one_to_four(n, expected):
    assert people(n) == expected


def test_a_count_of_things_is_judged_by_the_learners_behind_it():
    assert counted(300, 4) == {"value": None, "status": "suppressed"}                  # many attempts, but only four people
    assert counted(300, 5) == {"value": 300, "status": "ok"}
    assert counted(0, 0) == {"value": 0, "status": "ok"} and counted(7, 0) == {"value": 7, "status": "ok"}


# ---------- rates ----------
def test_a_rate_carries_its_numerator_and_denominator():
    assert rate(3, 4, 5) == {"numerator": 3, "denominator": 4, "rate": 0.75, "status": "ok"}
    assert rate(1, 3, 9)["rate"] == 0.3333 and rate(2, 3, 9)["rate"] == 0.6667 and rate(0, 10, 6) == {"numerator": 0, "denominator": 10, "rate": 0.0, "status": "ok"}


def test_an_empty_denominator_is_null_not_zero():
    r = rate(0, 0, 0)
    assert r == {"numerator": 0, "denominator": 0, "rate": None, "status": "no_data"} and r["rate"] is None
    assert rate(0, 0, 9)["status"] == "no_data" and rate(5, 0, 9)["rate"] is None


@pytest.mark.parametrize("learners", [1, 2, 3, 4])
def test_a_rate_over_fewer_than_five_learners_is_suppressed_with_its_parts(learners):
    assert rate(3, 4, learners) == {"numerator": None, "denominator": None, "rate": None, "status": "suppressed"}


def test_five_learners_is_enough():
    assert rate(3, 4, 5)["status"] == "ok"


@pytest.mark.parametrize("numerator_learners,status", [(0, "ok"), (1, "suppressed"), (4, "suppressed"), (5, "ok"), (20, "ok")])
def test_a_rate_whose_numerator_is_a_count_of_learners_is_suppressed_when_that_count_is_small(numerator_learners, status):
    r = rate(numerator_learners, 40, 40, numerator_learners)
    assert r["status"] == status and (r["rate"] is None) is (status == "suppressed")


# ---------- distributions and folding ----------
def keys(buckets):
    return [(b["key"], b["count"], b["status"]) for b in buckets]


def test_big_buckets_are_listed_as_they_are():
    d = distribution([("hi", "Hindi", 12), ("es", "Spanish", 7)])
    assert d["total"] == {"value": 19, "status": "ok"} and keys(d["buckets"]) == [("hi", 12, "ok"), ("es", 7, "ok")]


def test_zero_buckets_are_not_listed():
    assert keys(distribution([("hi", "Hindi", 12), ("es", "Spanish", 0)])["buckets"]) == [("hi", 12, "ok")]


def test_small_buckets_fold_into_other_which_is_shown_when_big_enough():
    d = distribution([("hi", "Hindi", 20), ("es", "Spanish", 3), ("fr", "French", 2)])
    assert keys(d["buckets"]) == [("hi", 20, "ok"), ("other", 5, "ok")] and d["total"]["value"] == 25


def test_a_single_small_bucket_cannot_be_recovered_by_subtraction():
    """Hindi 21, Spanish 4. Shown alone, 'Spanish 4' is hidden but total 25 minus Hindi 21 would give it back: so the smallest visible bucket joins 'other'."""
    d = distribution([("hi", "Hindi", 21), ("es", "Spanish", 4)])
    assert d["total"]["value"] == 25 and keys(d["buckets"]) == [("other", 25, "ok")]


def test_when_other_is_still_too_small_the_smallest_visible_bucket_joins_it():
    d = distribution([("a", "A", 30), ("b", "B", 6), ("c", "C", 2)])
    assert keys(d["buckets"]) == [("a", 30, "ok"), ("other", 8, "ok")]            # c (2) is too small; with b (6) it is 8


def test_if_nothing_can_make_other_big_enough_it_is_suppressed():
    d = distribution([("a", "A", 3), ("b", "B", 1)])
    assert d["total"] == {"value": None, "status": "suppressed"}
    assert keys(d["buckets"]) == [("other", None, "suppressed")] and d["buckets"][0]["learners"] is None


def test_no_learners_at_all_is_an_empty_distribution():
    assert distribution([]) == {"total": {"value": 0, "status": "ok"}, "buckets": []}


def test_folding_uses_the_measure_for_buckets_that_overlap():
    """Weaknesses: one learner can have several topic weaknesses, so the folded bucket is measured as a SET (here 3 distinct learners, not 1+1+1+1+1)."""
    items = [{"key": f"t{i}", "label": f"T{i}", "count": 1, "learners": 1} for i in range(5)] + [{"key": "big", "label": "Big", "count": 40, "learners": 20}]
    seen = []
    def measure(ks):
        seen.append(sorted(ks))
        return len(ks), 3                                                         # 5 weaknesses held by only 3 people
    out = fold_buckets(items, measure)
    assert [b["key"] for b in out] == ["other"] and out[0]["status"] == "suppressed" and out[0]["count"] is None
    assert seen[0] == ["t0", "t1", "t2", "t3", "t4"] and sorted(seen[-1]) == sorted(["t0", "t1", "t2", "t3", "t4", "big"])


def test_fold_keeps_the_visible_buckets_in_their_original_order():
    items = [{"key": "c", "label": "C", "count": 9, "learners": 9}, {"key": "a", "label": "A", "count": 7, "learners": 7}, {"key": "z", "label": "Z", "count": 2, "learners": 2},
             {"key": "b", "label": "B", "count": 3, "learners": 3}]
    out = fold_buckets(items, lambda ks: (sum({"z": 2, "b": 3}[k] for k in ks), sum({"z": 2, "b": 3}[k] for k in ks)))
    assert [b["key"] for b in out] == ["c", "a", "other"] and out[-1]["count"] == 5
