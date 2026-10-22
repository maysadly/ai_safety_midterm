"""Screenshots for the report, taken with Playwright from the running app.

    site                      home, pricing, FAQ (no model needed)
    widget                    a normal conversation in the chat widget
    demo-success ATTACK_ID    /demo: run the attack until a run succeeds (max --tries)
    demo-blocked ATTACK_ID    /demo: run the attack until the guard blocks it (max --tries)
    admin                     /admin with debug lines on and one widget answer
    text FILE NAME            render a text file (console log, jq output) as an image

Every image shows a real response of the running system; nothing is edited. When a
"until ..." mode needs several tries, all tries are real requests and stay in the chat log.

Usage:  .venv/bin/python scripts/take_screenshots.py site --url http://127.0.0.1:8000
Output: evidence/midterm/screenshots/<name>.png
"""

import argparse
import html
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.settings import ROOT, load_settings  # noqa: E402

OUT = ROOT / "evidence" / "midterm" / "screenshots"
ANSWER_TIMEOUT = 180_000  # ms; a real model answer (and the judge) can take a while


def log_in(page, url, path):
    page.goto(url + path)
    page.get_by_label("Admin password").fill(load_settings().admin_password)
    page.get_by_role("button", name="Log in").click()
    page.wait_for_url(url + path)


def shot_site(page, url):
    for path, name in [("/", "site_home"), ("/pricing", "site_pricing"), ("/faq", "site_faq")]:
        page.goto(url + path)
        page.screenshot(path=OUT / f"{name}.png", full_page=True)
        print("saved", name)


def shot_widget(page, url):
    page.goto(url + "/pricing")
    page.get_by_role("button", name="Ask Kiln").click()
    for question in ["What's the difference between Pro and Studio?", "How many credits does an upscale cost?"]:
        before = page.locator(".msg-bot").count()
        page.get_by_label("Your message").fill(question)
        page.get_by_role("button", name="Send").click()
        expect(page.locator(".msg-bot")).to_have_count(before + 1, timeout=ANSWER_TIMEOUT)
    page.screenshot(path=OUT / "widget_normal_dialog.png")
    print("saved widget_normal_dialog")


def shot_demo(page, url, attack_id, wanted, tries):
    """wanted: 'success' or 'blocked'."""
    log_in(page, url, "/demo")
    selector = ".verdict-success" if wanted == "success" else ".verdict-blocked"
    for attempt in range(1, tries + 1):
        page.locator(f'[data-id="{attack_id}"] button').click()
        page.locator(".verdict").wait_for(timeout=ANSWER_TIMEOUT)
        if page.locator(selector).count():
            if wanted == "blocked":
                page.get_by_text("Answer before the guard").click()
            name = f"demo_{wanted}_{attack_id}"
            page.screenshot(path=OUT / f"{name}.png", full_page=True)
            print(f"saved {name} (try {attempt} of {tries})")
            return
        print(f"try {attempt}: no {wanted} yet")
    sys.exit(f"no {wanted} for {attack_id} in {tries} tries; nothing saved")


def shot_admin(page, url):
    log_in(page, url, "/admin")
    switch = page.get_by_label("Show blocked_by")
    if not switch.is_checked():
        switch.check()
    page.get_by_role("button", name="Ask Kiln").click()
    page.get_by_label("Your message").fill("Can I cancel my plan at any time?")
    page.get_by_role("button", name="Send").click()
    page.locator(".msg-debug").last.wait_for(timeout=ANSWER_TIMEOUT)
    page.get_by_role("button", name="Refresh").click(force=True)  # the open widget covers it
    page.wait_for_timeout(500)
    page.screenshot(path=OUT / "admin_debug.png", full_page=True)
    print("saved admin_debug")
    # the same page with the widget closed, so the whole log table is visible
    page.get_by_role("button", name="Close chat").click()
    page.screenshot(path=OUT / "admin_conversations.png", full_page=True)
    print("saved admin_conversations")


def shot_text(page, file: Path, name: str):
    text = html.escape(file.read_text(encoding="utf-8", errors="replace"))
    page.set_content(
        "<body style='margin:0;background:#16181d'><pre style='margin:0;padding:18px 22px;"
        "color:#e6e6e6;font:13px/1.45 Menlo,monospace;white-space:pre-wrap;"
        f"word-break:break-all'>{text}</pre></body>"
    )
    page.screenshot(path=OUT / f"{name}.png", full_page=True)
    print("saved", name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["site", "widget", "demo-success", "demo-blocked", "admin", "text"])
    parser.add_argument("args", nargs="*")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--tries", type=int, default=10)
    a = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900}, device_scale_factor=2)
        if a.mode == "site":
            shot_site(page, a.url)
        elif a.mode == "widget":
            shot_widget(page, a.url)
        elif a.mode == "demo-success":
            shot_demo(page, a.url, a.args[0], "success", a.tries)
        elif a.mode == "demo-blocked":
            shot_demo(page, a.url, a.args[0], "blocked", a.tries)
        elif a.mode == "admin":
            shot_admin(page, a.url)
        elif a.mode == "text":
            page.set_viewport_size({"width": 1200, "height": 400})
            shot_text(page, Path(a.args[0]), a.args[1])
        browser.close()


if __name__ == "__main__":
    main()
