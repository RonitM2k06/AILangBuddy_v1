"""The gamification rules, in one place. Everything here is a constant or a pure function so it can be tested at its boundaries.
XP rewards only what the learner has already done in the existing tables; nothing is awarded for calling an API, and no
amount ever comes from a client."""

# XP per rewarded thing, credited ONCE per thing (exercise, lesson, situation, listening activity, speaking phrase, daily task).
XP_RULES = {"exercise": 5,        # the first correct answer to an exercise
            "lesson": 20,         # a completed lesson
            "situation": 25,      # a completed situation
            "listening": 5,       # the first correct answer to a listening activity
            "speaking": 10,       # the first completed speaking practice of a phrase
            "daily_task": 10}     # a daily-plan task that was really done (checked against the underlying progress)
ACTIVITY_KINDS = tuple(XP_RULES)               # challenge rewards are separate: they never count as activity or toward the cap
KIND_ORDER = {k: i for i, k in enumerate(("exercise", "listening", "speaking", "lesson", "situation", "daily_task"))}
DAILY_XP_CAP = 150                             # activity XP per local day; anything over is recorded as 0 XP

# Levels: level L starts at 50 * L * (L - 1) XP (1: 0, 2: 100, 3: 300, 4: 600, 5: 1000 ...). Separate from the CEFR level.
MAX_LEVEL = 20
RANKS = ((1, "Explorer"), (3, "Traveller"), (5, "Local"), (8, "Insider"), (12, "Native"))


def level_start(level):
    return 50 * level * (level - 1)


def level_for(xp):
    xp = max(0, xp)
    level = 1
    while level < MAX_LEVEL and xp >= level_start(level + 1):
        level += 1
    return level


def rank_for(level):
    name = RANKS[0][1]
    for minimum, label in RANKS:
        if level >= minimum:
            name = label
    return name


# Streaks and freezes
MAX_FREEZES = 2                                # also the database trigger's limit; a test ties them together
FREEZE_EVERY = 7                               # one freeze is earned on every 7th day of a streak

# Social
FRIEND_CODE_LENGTH = 10
MAX_FRIENDS = 30
MAX_PENDING_OUTGOING = 20
REJECT_COOLDOWN_DAYS = 7
CODE_MAX_FAILURES = 5
CODE_WINDOW_SECONDS = 900
SOCIAL_AGE_GROUPS = ("teen", "adult")          # the child age group has no social features, enforced by the server
