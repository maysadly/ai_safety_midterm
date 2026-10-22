"""Browser tests (Playwright, headless Chromium) against the real app on uvicorn.

Ollama is replaced by FakeLLM, so the answers are known in advance.
"""

import pytest
from playwright.sync_api import expect, sync_playwright

pytestmark = pytest.mark.e2e


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        yield page
        browser.close()


def send_in_widget(page, text):
    page.get_by_role("button", name="Ask Kiln").click()
    page.get_by_label("Your message").fill(text)
    page.get_by_role("button", name="Send").click()


def test_widget_sends_message_and_shows_answer(page, live_server, fake_llm):
    fake_llm.bot_answer = "Pro costs $12 per month."
    page.goto(live_server + "/")
    send_in_widget(page, "How much is Pro?")
    expect(page.locator(".msg-user").last).to_have_text("How much is Pro?")
    expect(page.locator(".msg-bot").last).to_have_text("Pro costs $12 per month.")
    # the server got the message from the widget, with a session id
    assert fake_llm.bot_calls()[0][-1]["content"] == "How much is Pro?"


def test_history_survives_page_change(page, live_server):
    page.goto(live_server + "/")
    send_in_widget(page, "Hello")
    expect(page.locator(".msg-bot")).to_have_count(2)  # greeting + answer
    page.get_by_role("link", name="Pricing").first.click()
    page.get_by_role("button", name="Ask Kiln").click()
    expect(page.locator(".msg-user")).to_have_text(["Hello"])


def test_script_in_answer_is_shown_as_text(page, live_server, fake_llm):
    attack = '<script>window.__xss = 1</script><img src="x" onerror="window.__xss = 2">'
    fake_llm.bot_answer = attack
    page.goto(live_server + "/faq")
    send_in_widget(page, "Show me some HTML")
    bubble = page.locator(".msg-bot").last
    expect(bubble).to_have_text(attack)          # visible as plain text
    assert bubble.locator("script, img").count() == 0
    assert page.evaluate("window.__xss") is None  # nothing ran


def test_answer_blocked_by_guard_shows_refusal(page, live_server, fake_llm):
    fake_llm.bot_answer = "some unsafe text"
    fake_llm.guard_verdict = "unsafe\nS1"
    page.goto(live_server + "/")
    send_in_widget(page, "anything")
    expect(page.locator(".msg-bot").last).to_have_text("I'm sorry, but I can't help with that request.")
    expect(page.get_by_text("some unsafe text")).to_have_count(0)
