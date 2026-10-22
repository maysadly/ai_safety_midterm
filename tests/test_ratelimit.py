"""Rate limit: unit test with a fake clock, and through the API."""

import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.ratelimit import RateLimiter


def test_limit_per_minute_with_fake_clock():
    now = [0.0]
    limiter = RateLimiter(3, clock=lambda: now[0])
    assert [limiter.allow("ip") for _ in range(4)] == [True, True, True, False]
    assert limiter.allow("other-ip")  # keys are counted separately
    now[0] = 60.0
    assert limiter.allow("ip")  # a minute later the old requests no longer count


def test_api_returns_429_and_logs_it(make_settings, fake_llm):
    settings = make_settings(RATE_LIMIT_ENABLED="true", RATE_LIMIT_PER_MINUTE="2")
    client = TestClient(create_app(settings, fake_llm))
    codes = [client.post("/api/chat", json={"message": "hi"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    last = json.loads(settings.chat_log_path.read_text().splitlines()[-1])
    assert last["blocked_by"] == "rate_limit"
    assert len(fake_llm.bot_calls()) == 2  # the blocked request never reached the model


def test_switched_off_for_experiment_runs(make_settings, fake_llm):
    settings = make_settings(RATE_LIMIT_ENABLED="false", RATE_LIMIT_PER_MINUTE="2")
    client = TestClient(create_app(settings, fake_llm))
    assert all(client.post("/api/chat", json={"message": "hi"}).status_code == 200 for _ in range(5))
