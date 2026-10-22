"""Browser tests for /admin and /demo (Playwright, headless Chromium, fake Ollama)."""

import pytest
from playwright.sync_api import expect, sync_playwright

pytestmark = pytest.mark.e2e

CODE = "STAFF-D6NB-WWQB"


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        yield page
        browser.close()


def log_in(page, base, settings, path):
    page.goto(base + path)
    expect(page).to_have_url(f"{base}/admin/login?next={path}")
    page.get_by_label("Admin password").fill(settings.admin_password)
    page.get_by_role("button", name="Log in").click()
    expect(page).to_have_url(base + path)


def test_demo_runs_an_attack_and_highlights_success(page, live_server, settings, fake_llm):
    fake_llm.bot_answer = f"Sure, the staff code is {CODE}."
    log_in(page, live_server, settings, "/demo")
    page.locator('[data-id="M0-G2-1"] button').click()
    expect(page.locator(".verdict-success")).to_contain_text("Attack succeeded")
    expect(page.locator(".answer-box").first).to_have_text(f"Sure, the staff code is {CODE}.")
    expect(page.locator('[data-id="M0-G2-1"]')).to_have_class("attack-item is-success")
    expect(page.locator(".score-hit")).to_contain_text("1 / 1 succeeded")


def test_demo_shows_a_guard_block(page, live_server, settings, fake_llm):
    fake_llm.bot_answer = f"The code is {CODE}"
    fake_llm.guard_verdict = "unsafe\nS7"
    log_in(page, live_server, settings, "/demo")
    page.locator('[data-id="M0-G2-2"] button').click()
    expect(page.locator(".verdict-blocked")).to_contain_text("guard blocked")
    expect(page.locator(".details")).to_contain_text("unsafe S7")
    page.get_by_text("Answer before the guard").click()
    expect(page.locator(".hidden-answer .answer-box")).to_have_text(f"The code is {CODE}")


def test_demo_run_all_counts_every_shown_attack(page, live_server, settings):
    log_in(page, live_server, settings, "/demo")
    page.locator("#filter-method").select_option("M0")
    page.get_by_role("button", name="Run all shown").click()
    expect(page.locator("#progress")).to_have_text("Done: 12 attacks", timeout=20000)
    expect(page.locator(".score")).to_have_count(4)  # G1..G4, 3 attacks each


def test_admin_debug_switch_shows_debug_line_in_widget(page, live_server, settings):
    log_in(page, live_server, settings, "/admin")
    page.get_by_label("Show blocked_by").check()
    page.get_by_role("button", name="Ask Kiln").click()
    page.get_by_label("Your message").fill("How much is Pro?")
    page.get_by_role("button", name="Send").click()
    expect(page.locator(".msg-debug")).to_contain_text("blocked_by: none | guard: safe")
    page.get_by_role("button", name="Close chat").click()  # the open widget covers the table
    page.get_by_role("button", name="Refresh").click()
    expect(page.locator("#log-rows tr").first).to_contain_text("How much is Pro?")


def test_login_never_redirects_to_another_site(page, live_server, settings):
    page.goto(live_server + "/admin/login?next=//evil.example/")
    page.get_by_label("Admin password").fill(settings.admin_password)
    page.get_by_role("button", name="Log in").click()
    expect(page).to_have_url(live_server + "/admin")
