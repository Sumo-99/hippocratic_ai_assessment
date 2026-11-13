"""build_client(): provider selection, and the rule that only the factory names a concrete client."""
import pathlib

import pytest

from storyteller import config
from storyteller.clients import build_client
from storyteller.llm import OpenRouterClient
from storyteller.llm_anthropic import AnthropicClient

ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def keys(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


def test_default_is_openrouter(monkeypatch):
    monkeypatch.setattr(config, "PROVIDER", "openrouter")
    assert isinstance(build_client(), OpenRouterClient)


def test_anthropic_selected_from_config(monkeypatch):
    monkeypatch.setattr(config, "PROVIDER", "anthropic")
    on_usage = lambda *a: None
    client = build_client(on_usage=on_usage)
    assert isinstance(client, AnthropicClient) and client.on_usage is on_usage


def test_provider_is_normalized():
    assert isinstance(build_client(provider=" Anthropic "), AnthropicClient)


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="openrouter, anthropic"):
        build_client(provider="anthorpic")


def test_only_factory_names_concrete_clients():
    """Callers must go through build_client(), so swapping backends never touches them."""
    allowed = {"llm.py", "llm_anthropic.py", "clients.py"}
    files = [p for p in (ROOT / "storyteller").rglob("*.py") if p.name not in allowed]
    files += list(ROOT.glob("*.py"))  # main.py, ui.py
    offenders = [str(p.relative_to(ROOT)) for p in files
                 if "OpenRouterClient(" in p.read_text() or "AnthropicClient(" in p.read_text()]
    assert offenders == []
