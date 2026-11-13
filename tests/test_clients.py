"""build_client() is the only place that constructs the LLM client."""
import pathlib

from storyteller.clients import build_client
from storyteller.llm import AnthropicClient

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_builds_anthropic_client_wired_to_callback(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    on_usage = lambda *a: None
    client = build_client(on_usage=on_usage)
    assert isinstance(client, AnthropicClient) and client.on_usage is on_usage
    assert build_client() is not client  # a fresh client (and budget) per run


def test_only_factory_names_the_client():
    """Callers must go through build_client(), so a backend change never touches them."""
    allowed = {"llm.py", "clients.py"}
    files = [p for p in (ROOT / "storyteller").rglob("*.py") if p.name not in allowed]
    files += list(ROOT.glob("*.py"))  # main.py, ui.py
    offenders = [str(p.relative_to(ROOT)) for p in files if "AnthropicClient(" in p.read_text()]
    assert offenders == []
