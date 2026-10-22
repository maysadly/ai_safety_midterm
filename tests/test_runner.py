"""scripts/run_attacks.py against the real app on uvicorn (fake Ollama)."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_attacks.py"


@pytest.fixture
def runner():
    spec = importlib.util.spec_from_file_location("run_attacks", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_writes_one_line_per_attempt_and_resumes(runner, live_server, tmp_path, monkeypatch, settings):
    out = tmp_path / "attempts.jsonl"
    argv = ["run_attacks.py", "--url", live_server, "--repeats", "2", "--methods", "M0", "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    runner.main()
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(rows) == 12 * 2
    assert len({(r["attack_id"], r["repeat"]) for r in rows}) == 24  # every attack once per repeat
    assert all(r["model_violated"] is False for r in rows)  # the fake bot always answers about prices
    # the runner's requests are in the chat log with source "runner"
    chat_log = [json.loads(line) for line in settings.chat_log_path.read_text().splitlines()]
    assert sum(e["source"] == "runner" for e in chat_log) == 24

    runner.main()  # second start: nothing left to do
    assert len(out.read_text().splitlines()) == 24
