"""Website pages, security headers and settings checks."""

from pathlib import Path

import pytest

from app.settings import load_settings

FOOTER = "Fictional company — student demo project (QAIRU, AISRA1301)"
STATIC = Path(__file__).resolve().parent.parent / "app" / "static"


@pytest.mark.parametrize("path", ["/", "/pricing", "/faq", "/about"])
def test_pages_have_footer_and_chat_widget(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert FOOTER in response.text
    assert "/static/js/chat-widget.js" in response.text


def test_security_headers(client):
    headers = client.get("/").headers
    assert "script-src 'self'" in headers["content-security-policy"]
    assert headers["x-content-type-options"] == "nosniff"


def test_widget_never_inserts_html():
    """Model answers are untrusted: the widget must only use textContent."""
    code = (STATIC / "js" / "chat-widget.js").read_text()
    assert ".innerHTML" not in code  # the property; the word itself appears in a comment
    assert ".outerHTML" not in code
    assert "insertAdjacentHTML" not in code
    assert "textContent" in code


def test_health_reports_prompt_hash(client, settings):
    assert client.get("/health").json()["system_prompt_sha256"] == settings.system_prompt_sha256


def test_api_docs_are_off(client):
    assert client.get("/docs").status_code == 404


def test_missing_admin_password_stops_the_app(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    monkeypatch.setenv("COOKIE_SECRET", "x" * 20)
    with pytest.raises(RuntimeError):
        load_settings(env_file=None)
