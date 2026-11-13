"""The one place that constructs the LLM client. Everything else asks build_client(), so a
change of backend touches this file and llm.py only."""
from typing import Callable

from .llm import AnthropicClient, LLMClient


def build_client(on_usage: Callable | None = None) -> LLMClient:
    """A fresh client for one run (the budget guard is per client instance)."""
    return AnthropicClient(on_usage=on_usage)
