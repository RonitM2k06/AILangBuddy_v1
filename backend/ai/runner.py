"""Runs a provider call with a hard time limit and turns every failure into an AiError with a safe code."""
import concurrent.futures
import logging

from .. import settings
from .base import AiError

log = logging.getLogger(__name__)
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="ai")


def run(fn, *args):
    future = _EXECUTOR.submit(fn, *args)
    try:
        return future.result(timeout=settings.ai_timeout_seconds())
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise AiError("timeout")
    except AiError:
        raise
    except Exception:                                       # a bug in a provider must not reach the learner or crash the request
        log.exception("AI provider failed unexpectedly")
        raise AiError("provider_error")
