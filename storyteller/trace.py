"""Records one pipeline run (inputs, decisions, timings, cost) and writes it as JSON."""
import json
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config


class Trace:
    def __init__(self, request: str):
        self.request = request
        self.data: dict = {}
        self.timings: dict[str, float] = {}
        self.calls: list[dict] = []

    def set(self, key, value):
        self.data[key] = value

    def append(self, key, value):
        self.data.setdefault(key, []).append(value)

    @contextmanager
    def stage(self, name: str):
        start = time.monotonic()
        try:
            yield
        finally:  # still record time if the stage raises
            self.timings[name] = self.timings.get(name, 0.0) + time.monotonic() - start

    def on_usage(self, stage, prompt_tokens, completion_tokens, cost, seconds):
        self.calls.append({"stage": stage, "prompt_tokens": prompt_tokens,
                           "completion_tokens": completion_tokens, "cost_usd": cost,
                           "seconds": round(seconds, 3)})

    def write(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", self.request.lower()).strip("-")[:40] or "request"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        os.makedirs(config.RUNS_DIR, exist_ok=True)
        path = os.path.join(config.RUNS_DIR, f"{stamp}-{slug}.json")
        doc = {"request": self.request, **self.data, "timings": self.timings,
               "calls": self.calls,
               "total_cost_usd": round(sum(c["cost_usd"] for c in self.calls), 6)}
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)
        return path
