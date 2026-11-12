import asyncio

import pytest


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Retry backoff must not slow tests down."""
    async def instant(_seconds):
        return None
    monkeypatch.setattr(asyncio, "sleep", instant)
