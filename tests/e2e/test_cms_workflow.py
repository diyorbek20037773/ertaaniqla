"""M7 gate: editor creates an article in ru → translates it to uz → medical reviewer approves →
the page is live in both languages with the "verified by a doctor" badge.

Runs against a live dev/staging server with the demo accounts:

    docker compose exec web python manage.py create_demo_staff
    E2E_BASE_URL=http://localhost:8001 make e2e

Also refreshes the CMS screenshots used by docs/EDITOR_GUIDE_ru.md / _uz.md
(tests/e2e/screenshots/cms-*.png).
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any

import pytest
from django_otp.oath import totp

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8001")
SCREENSHOTS = Path(__file__).parent / "screenshots"
DESKTOP = {"width": 1280, "height": 900}

# defaults of apps/users/management/commands/create_demo_staff.py (dev/UAT only)
DEMO_PASSWORD = os.environ.get("E2E_DEMO_PASSWORD", "demo-Erta-aniqla-2026")
DEMO_TOTP_KEY = bytes.fromhex(
    os.environ.get("E2E_DEMO_TOTP_KEY", "3132333435363738393031323334353637383930")
)
UZ_LOCALE_LABEL = "Oʻzbekcha"


def shot(page: Any, name: str) -> None:
    SCREENSHOTS.mkdir(exist_ok=True)
    page.wait_for_timeout(400)  # let dropdown/tab transitions finish
    page.screenshot(path=str(SCREENSHOTS / f"cms-{name}.png"), full_page=False)


def cms_login(browser: Any, username: str, screenshots: bool = False) -> Any:
    context = browser.new_context(
        viewport=DESKTOP, locale="ru-RU", extra_http_headers={"X-E2E": "1"}
    )
    page = context.new_page()
    page.goto(f"{BASE_URL}/cms/login/")
    if screenshots:
        shot(page, "01-login")
    page.fill("input[name=username]", username)
    page.fill("input[name=password]", DEMO_PASSWORD)
    page.click("form button[type=submit]")
    page.wait_for_load_state()
    if "/2fa/auth" not in page.url:
        pytest.fail(
            f"{username}: expected the 2FA step, got {page.url}. "
            "Run `manage.py create_demo_staff` on the server first."
        )
    if screenshots:
        shot(page, "02-2fa-code")
    # the same TOTP code cannot be used twice (demo users share a key): retry on the next step
    for _ in range(3):
        page.fill("input[name=otp_token]", f"{totp(DEMO_TOTP_KEY):06d}")
        page.click("form button[type=submit] >> nth=0")
        page.wait_for_load_state()
        if "/2fa/" not in page.url:
            break
        time.sleep(31 - time.time() % 30)
    assert page.url.rstrip("/").endswith("/cms"), page.url
    return page


def page_id(page: Any, **params: str) -> int:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    response = page.request.get(f"{BASE_URL}/cms/api/main/pages/?{query}&limit=20")
    assert response.ok, response.status
    items = response.json()["items"]
    assert len(items) == 1, items
    return int(items[0]["id"])


def open_actions_menu(page: Any) -> None:
    page.locator("footer .w-dropdown__toggle").first.click()


def submit_for_moderation(page: Any, screenshot: str | None = None) -> None:
    open_actions_menu(page)
    if screenshot:
        shot(page, screenshot)
    page.locator("footer button[name=action-submit]").click()
    page.wait_for_load_state()


def fill_article(page: Any, title: str, summary: str, slug: str) -> None:
    page.fill("input[name=title]", title)
    page.fill("input[name=summary]", summary)
    # tab ids are slugs of the translated headings (cached per process) — select by position
    tabs = page.locator("[role=tab]")
    tabs.nth(1).click()  # Promote
    page.fill("input[name=slug]", slug)
    tabs.nth(0).click()  # Content


def approve(page: Any, pid: int, screenshot: str | None = None) -> None:
    page.goto(f"{BASE_URL}/cms/pages/{pid}/edit/")
    open_actions_menu(page)
    if screenshot:
        shot(page, screenshot)
    page.locator(
        "footer button[data-workflow-action-name=approve]:not([data-workflow-action-modal-url])"
    ).click()
    page.wait_for_load_state()


def test_editor_ru_article_translated_to_uz_approved_by_reviewer_live_in_both(browser) -> None:
    tag = uuid.uuid4().hex[:6]
    ru_slug, uz_slug = f"e2e-statya-{tag}", f"e2e-maqola-{tag}"

    # 1. editor creates the article in Russian and submits it for medical review
    editor = cms_login(browser, "demo-editor", screenshots=True)
    shot(editor, "03-dashboard-editor")
    parent = page_id(editor, locale="ru", slug="osvedomlennost")
    editor.goto(f"{BASE_URL}/cms/pages/add/articles/articlepage/{parent}/")
    fill_article(editor, f"E2E статья {tag}", "Краткое описание для проверки процесса.", ru_slug)
    shot(editor, "04-add-article")
    # editors have no "Publish" action
    open_actions_menu(editor)
    assert editor.locator("footer button[name=action-publish]").count() == 0
    open_actions_menu(editor)
    submit_for_moderation(editor, screenshot="05-submit-for-moderation")
    ru_id = page_id(editor, slug=ru_slug)

    # 2. editor translates it into Uzbek (wagtail-localize, simple mode) and submits that too
    editor.goto(f"{BASE_URL}/cms/localize/submit/page/{ru_id}/")
    editor.get_by_label(UZ_LOCALE_LABEL).check()
    shot(editor, "06-translate-submit")
    editor.locator("main form [type=submit]").click()
    editor.wait_for_load_state()
    assert "/edit/" in editor.url, editor.url
    fill_article(
        editor, f"E2E maqola {tag}", "Jarayonni tekshirish uchun qisqacha tavsif.", uz_slug
    )
    shot(editor, "07-translation-edit-uz")
    submit_for_moderation(editor)
    uz_id = page_id(editor, slug=uz_slug)
    assert uz_id != ru_id

    anonymous = browser.new_context(extra_http_headers={"X-E2E": "1"})
    ru_url = f"{BASE_URL}/ru/zhenskiy/osvedomlennost/{ru_slug}/"
    uz_url = f"{BASE_URL}/uz/ayollar/ogohlik/{uz_slug}/"
    assert anonymous.request.get(ru_url).status == 404  # nothing is public before review

    # 3. the medical reviewer sees both pages on the dashboard and approves them
    reviewer = cms_login(browser, "demo-reviewer")
    reviewer.goto(f"{BASE_URL}/cms/")
    dashboard = reviewer.content()
    assert f"E2E статья {tag}" in dashboard and f"E2E maqola {tag}" in dashboard
    shot(reviewer, "08-dashboard-reviewer")
    approve(reviewer, ru_id, screenshot="09-approve")
    approve(reviewer, uz_id)

    # 4. live in both languages, with the badge, and the language switch connects them
    for url, title in ((ru_url, f"E2E статья {tag}"), (uz_url, f"E2E maqola {tag}")):
        response = anonymous.request.get(url)
        assert response.status == 200, url
        html = response.text()
        assert title in html
        assert "verified-badge" in html
        assert "Demo Shifokor" in html
    public = anonymous.new_page()
    public.goto(uz_url)
    assert public.locator(f'link[rel=alternate][hreflang=ru][href$="/{ru_slug}/"]').count() == 1
    shot(public, "10-live-with-badge")

    for context in (editor.context, reviewer.context, anonymous):
        context.close()
