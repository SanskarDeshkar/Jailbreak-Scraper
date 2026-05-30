"""Rendered HTML fetching utilities for the Jailbreak barter tracker."""

from __future__ import annotations

from playwright.sync_api import sync_playwright


def fetch_url(url: str, timeout: float = 30.0) -> str | None:
    """Render a URL in a headless browser and return the fully loaded HTML."""
    timeout_ms = int(timeout * 1000)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(5000)

        all_cards_html = set()
        for _ in range(50):
            current_cards = page.evaluate(
                "() => Array.from(document.querySelectorAll('div[data-slot=\"card\"]')).map(el => el.outerHTML)"
            )
            all_cards_html.update(current_cards)
            page.keyboard.press("PageDown")
            page.wait_for_timeout(2000)

        current_cards = page.evaluate(
            "() => Array.from(document.querySelectorAll('div[data-slot=\"card\"]')).map(el => el.outerHTML)"
        )
        all_cards_html.update(current_cards)

        page.keyboard.press("End")
        page.wait_for_timeout(2000)
        current_cards = page.evaluate(
            "() => Array.from(document.querySelectorAll('div[data-slot=\"card\"]')).map(el => el.outerHTML)"
        )
        all_cards_html.update(current_cards)

        browser.close()
        return "<div>" + "".join(all_cards_html) + "</div>"
