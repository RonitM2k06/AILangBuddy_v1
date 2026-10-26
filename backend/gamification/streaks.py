"""Streak and freeze arithmetic as a pure function of the days the learner was active, the freeze ledger and today.

Rules
  * A day is active if the learner did something that earns XP on it (the day is the learner's local date).
  * The streak is the run of consecutive days; repeating activity on one day never adds to it.
  * A missed day does not break the streak if a freeze protects it. Freezes are used only when the learner comes back (on the
    next active day), one per missed day, all or nothing: with not enough freezes for the whole gap the streak restarts and no
    freeze is spent. A protected day keeps the run going but is not counted as an active day.
  * One freeze is earned on every 7th day of a run (dated by that day), up to MAX_FREEZES held.
  * The current streak is alive through today and yesterday (today may still be to come); older than that, it is 0."""
from dataclasses import dataclass, field
from datetime import timedelta

from . import rules


@dataclass
class StreakResult:
    current: int = 0
    longest: int = 0
    active_today: bool = False
    at_risk: bool = False                       # active yesterday, not yet today
    new_used: list = field(default_factory=list)      # freeze days to record
    new_earned: list = field(default_factory=list)    # freeze credits to record


def compute(days, used, earned, today, max_freezes=rules.MAX_FREEZES, every=rules.FREEZE_EVERY):
    days = sorted(set(days))
    used, earned = set(used), set(earned)
    out = StreakResult()
    run, last = 0, None
    for d in days:
        if last is None:
            run = 1
        else:
            gap = (d - last).days - 1
            if gap == 0:
                run += 1
            else:
                missed = [last + timedelta(days=i) for i in range(1, gap + 1)]
                need = [m for m in missed if m not in used]
                balance = sum(1 for e in earned if e <= last) - sum(1 for u in used if u < missed[0])
                if len(need) <= balance:
                    for m in need:
                        used.add(m)
                        out.new_used.append(m)
                    run += 1
                else:
                    run = 1
        if run % every == 0 and d not in earned:
            balance = sum(1 for e in earned if e <= d) - sum(1 for u in used if u <= d)
            if balance < max_freezes:
                earned.add(d)
                out.new_earned.append(d)
        out.longest = max(out.longest, run)
        last = d
    if last is not None and (today - last).days <= 1:
        out.current = run
        out.active_today = last == today
        out.at_risk = last == today - timedelta(days=1)
    return out
