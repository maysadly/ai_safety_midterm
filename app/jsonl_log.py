"""Append-only JSONL log: one JSON object per line.

Used for two files: the chat log (one line per /api/chat request) and the
evaluation log (one line per evaluated attack). Experiment scripts, /admin and
/demo all read the same files, so what the UI shows is what is in the log.
"""

import json
import threading
from pathlib import Path


class JsonlLog:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def write(self, entry: dict) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self._lock, self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def last(self, n: int) -> list[dict]:
        return self.read_all()[-n:]

    def find(self, key: str, value: str) -> dict | None:
        """Last entry whose `key` equals `value` (e.g. find("request_id", "...")), or None."""
        for entry in reversed(self.read_all()):
            if entry.get(key) == value:
                return entry
        return None
