"""The one place that picks a concrete LLM client. Everything else asks build_client()."""
from typing import Callable

from . import config
from .llm import LLMClient

PROVIDERS = ("openrouter", "anthropic")


def build_client(on_usage: Callable | None = None, provider: str | None = None) -> LLMClient:
    """A fresh client for one run. `provider` defaults to config.PROVIDER (env LLM_PROVIDER)."""
    name = (provider or config.PROVIDER).strip().lower()
    if name == "openrouter":
        from .llm import OpenRouterClient
        return OpenRouterClient(on_usage=on_usage)
    if name == "anthropic":
        # Imported here so OpenRouter users never import the anthropic package.
        from .llm_anthropic import AnthropicClient
        return AnthropicClient(on_usage=on_usage)
    raise ValueError(f"LLM_PROVIDER must be one of: {', '.join(PROVIDERS)} (got {name!r})")
