"""Smoke test against the real Ollama with the real models. Run by hand:

    bash scripts/start_ollama_local.sh
    .venv/bin/python -m pytest -m live -v
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

pytestmark = pytest.mark.live


def test_real_models_answer_a_pricing_question(settings):
    client = TestClient(create_app(settings))  # no fake: the real OllamaClient
    client.app.state.debug_lines = True
    response = client.post("/api/chat", json={"message": "How much does the Pro plan cost per month?"})
    assert response.status_code == 200
    body = response.json()
    assert "12" in body["reply"]
    assert body["debug"]["guard_verdict"] == "safe"
    assert body["debug"]["blocked_by"] is None

    entry = json.loads(settings.chat_log_path.read_text().splitlines()[-1])
    assert entry["model_answer"] == body["reply"]
    assert entry["t_model_ms"] > 0 and entry["t_guard_ms"] > 0
