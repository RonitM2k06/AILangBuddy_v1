"""Which provider runs. `offline()` is the built-in deterministic one. `FACTORY` is what the domain code asks for teen and adult
learners; tests replace it. Children never get anything but `offline()`: the services enforce that, not the factory."""
from .. import settings
from . import llm
from .mock import MockProvider


def offline():
    return MockProvider()


def configured():
    """The provider for teen and adult learners. 'mock' unless AI_PROVIDER=llm AND an LLM is configured; otherwise the built-in one."""
    if settings.ai_provider_name() == "llm" and llm.configured():
        return llm.LLMProvider()
    return offline()


FACTORY = configured
