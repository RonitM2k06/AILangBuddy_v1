"""Every threshold used to detect weaknesses, adapt difficulty and recommend. Deterministic, no learned parameters,
no LLM: change a number here and the behaviour (and the tests that pin it) change with it."""

# --- weakness: low accuracy in a topic ---
TOPIC_WINDOW = 10               # look at the learner's most recent N graded answers in the topic
TOPIC_MIN_ATTEMPTS = 6          # ...and need at least this many before judging at all
TOPIC_MIN_INCORRECT = 3         # ...and at least this many wrong answers (never a verdict from a couple of slips)
TOPIC_WEAK_BELOW = 0.60         # accuracy below this is a weakness
TOPIC_HIGH_BELOW = 0.40         # severity high below this, medium below TOPIC_MEDIUM_BELOW, otherwise low
TOPIC_MEDIUM_BELOW = 0.50

# --- weakness: the same vocabulary item keeps going wrong ---
ITEM_MIN_INCORRECT = 3          # wrong this many times in total, and the latest answer is still wrong
ITEM_MEDIUM_AT = 4
ITEM_HIGH_AT = 5

# --- adaptive difficulty (exercise difficulty scale: 1 easy, 2 medium, 3 hard) ---
DIFFICULTY_MIN = 1
DIFFICULTY_MAX = 3
DIFFICULTY_LABELS = {1: "easy", 2: "medium", 3: "hard"}
DIFFICULTY_WINDOW = 8           # recent graded lesson exercises considered
DIFFICULTY_MIN_ATTEMPTS = 5     # below this, stay at the starting level
STEP_UP_ACCURACY = 0.80         # at or above: one level harder than the learner has been working at
STEP_DOWN_BELOW = 0.50          # below: one level easier

# --- recommendations and the daily plan ---
LOW_CONFIDENCE_AT_OR_BELOW = 50
CHECKIN_MIN_ATTEMPTS = 3        # ask for a confidence rating once the learner has practised a topic this much
MAX_RECOMMENDATIONS = 6
DAILY_TASK_LIMIT = 3
