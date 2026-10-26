"""Sliding-window limiters for authentication (Phase 14C). In memory and per process: they reset on restart and are not shared between
workers, so several workers multiply every limit. They slow online guessing and spam on a single-process deployment; a shared store
would be needed beyond that.

Memory is bounded whatever an attacker sends: each limiter remembers at most THROTTLE_MAX_KEYS keys. When a new key would exceed that,
keys whose window has passed are dropped first, then the longest-remembered keys. Limits (overridable through the environment, see
settings.throttle_limit) and windows are read on every call.

Concurrency (Phase 14F): requests run on several threads, and checking a password is slow. `acquire` checks and counts an attempt in one
locked step BEFORE the password is checked, so concurrent requests cannot all pass the check before any of them is counted; an attempt that
turns out not to be a failure is given back with `release` (or `clear`)."""
import math
import threading

from .. import settings


class Limiter:
    def __init__(self, limit_name, window_name):
        self._limit_name, self._window_name = limit_name, window_name
        self._events = {}                       # key -> times (datetime) of counted events, oldest first
        self._lock = threading.RLock()

    @property
    def limit(self):
        return settings.throttle_limit(self._limit_name)

    @property
    def window(self):
        return getattr(settings, self._window_name)

    def _recent(self, key, now):
        return [t for t in self._events.get(key, ()) if (now - t).total_seconds() < self.window]

    def retry_after(self, key, now):
        """None if `key` may try now, otherwise whole seconds until it may (at least 1)."""
        with self._lock:
            recent = self._recent(key, now)
            if key in self._events:
                self._events[key] = recent
            if len(recent) >= self.limit:
                return max(1, math.ceil(self.window - (now - recent[0]).total_seconds()))
            return None

    def record(self, key, now):
        with self._lock:
            recent = self._recent(key, now)
            if key not in self._events and len(self._events) >= settings.THROTTLE_MAX_KEYS:
                for stale in [k for k, times in self._events.items() if not times or (now - times[-1]).total_seconds() >= self.window]:
                    del self._events[stale]
                while len(self._events) >= settings.THROTTLE_MAX_KEYS:
                    del self._events[next(iter(self._events))]
            recent.append(now)
            self._events[key] = recent

    def acquire(self, key, now):
        """Check and count one attempt in one step: None if `key` may try now (the attempt is counted), otherwise the wait in seconds
        (nothing counted)."""
        with self._lock:
            wait = self.retry_after(key, now)
            if wait is None:
                self.record(key, now)
            return wait

    def release(self, key, when):
        """Give back one attempt counted at `when` by acquire (it turned out not to be a failure)."""
        with self._lock:
            times = self._events.get(key)
            if times and when in times:
                times.remove(when)

    def clear(self, key):
        with self._lock:
            self._events.pop(key, None)

    def reset(self):
        with self._lock:
            self._events.clear()

    def __len__(self):
        return len(self._events)


login_account = Limiter("LOGIN_ACCOUNT_MAX_FAILURES", "LOGIN_WINDOW_SECONDS")    # key: normalised email (known or not: same treatment)
login_ip = Limiter("LOGIN_IP_MAX_FAILURES", "LOGIN_WINDOW_SECONDS")              # key: client address
register_ip = Limiter("REGISTER_IP_MAX", "REGISTER_WINDOW_SECONDS")              # key: client address
password_change = Limiter("PASSWORD_CHANGE_MAX_FAILURES", "PASSWORD_CHANGE_WINDOW_SECONDS")   # key: user id

ALL = (login_account, login_ip, register_ip, password_change)


def reset_all():
    for limiter in ALL:
        limiter.reset()
