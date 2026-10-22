"""Shared test fixtures.

FakeLLM stands in for Ollama: it records every call (model + messages) and
returns answers that the test chose, so the tests run without any model.
"""

import json
import socket
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import CONFIGS, load_settings

BOT_ANSWER = "The Pro plan costs $12 per month."
MODELS = json.loads((CONFIGS / "bot.json").read_text())


class FakeLLM:
    def __init__(self):
        self.calls = []                 # list of (model, messages)
        self.bot_answer = BOT_ANSWER
        self.guard_verdict = "safe"
        self.bot_error = None           # set to an Exception to simulate Ollama being down
        self.guard_error = None

    def chat(self, model, messages, options, format=None):
        self.calls.append((model, messages))
        if model == MODELS["guard_model"]:
            if self.guard_error:
                raise self.guard_error
            return self.guard_verdict
        if self.bot_error:
            raise self.bot_error
        return self.bot_answer

    def bot_calls(self):
        return [messages for model, messages in self.calls if model == MODELS["bot_model"]]


@pytest.fixture
def make_settings(tmp_path, monkeypatch):
    """Settings from test values only (the real .env is not read)."""

    def make(**env):
        values = {
            "ADMIN_PASSWORD": "test-password-123",
            "COOKIE_SECRET": "test-cookie-secret-0123456789",
            "IP_HASH_SALT": "test-salt",
            "RATE_LIMIT_ENABLED": "false",
            "DEBUG_LINES": "false",
            "CHAT_LOG_PATH": str(tmp_path / "chat.jsonl"),
            "EVAL_LOG_PATH": str(tmp_path / "evaluations.jsonl"),
        }
        values.update(env)
        for key, value in values.items():
            monkeypatch.setenv(key, value)
        return load_settings(env_file=None)

    return make


@pytest.fixture
def settings(make_settings):
    return make_settings()


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def client(settings, fake_llm):
    return TestClient(create_app(settings, fake_llm))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_server(settings, fake_llm):
    """The real app served by uvicorn in a background thread (for Playwright tests)."""
    port = free_port()
    server = uvicorn.Server(
        uvicorn.Config(create_app(settings, fake_llm), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)
