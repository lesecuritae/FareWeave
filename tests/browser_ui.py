"""Live browser regression; run against the started Compose app with Playwright installed."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

BASE_URL = os.getenv("FAREWEAVE_TEST_URL", "http://127.0.0.1:8791")
ARTIFACTS = Path(os.getenv("FAREWEAVE_BROWSER_ARTIFACTS", ".browser-artifacts"))


async def check_viewport(browser, width: int, height: int) -> None:
    page = await browser.new_page(viewport={"width": width, "height": height})
    errors = []
    page.on("console", lambda message: errors.append(f"console:{message.type}:{message.text}") if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(f"page:{error}"))
    await page.goto(BASE_URL, wait_until="networkidle")
    assert await page.locator("body").evaluate("el => el.scrollWidth <= el.clientWidth"), f"horizontale Überbreite bei {width}x{height}"
    if width <= 620:
        assert await page.locator(".topbar").evaluate("el => getComputedStyle(el).position") == "static"
    await page.locator("#calendarToggle").click()
    assert await page.locator("#calendarPanel").is_visible()
    assert await page.locator("#calendarDays button:not([disabled])").count() >= 20
    await page.screenshot(path=ARTIFACTS / f"fareweave-{width}x{height}.png", full_page=True)
    assert not errors, errors
    await page.close()


async def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        for viewport in ((360, 800), (390, 844), (412, 915), (1440, 1000)):
            await check_viewport(browser, *viewport)
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        await page.goto(BASE_URL)
        await page.locator("#origin").fill("Leipzig Hbf")
        await page.locator("#destination").fill("Dortmund Hbf")
        await page.locator("#departureDate").fill("2026-08-24")
        await page.locator("#departureAfter").fill("14:00")
        await page.locator("#oneWayButton").click()
        await page.locator("#searchButton").click()
        await page.locator("#searchProgress").wait_for(state="visible")
        assert await page.locator(".progress-step").count() == 6
        await page.locator("#results").wait_for(state="visible", timeout=150_000)
        await page.locator("#searchProgress").wait_for(state="hidden", timeout=5_000)
        assert await page.locator(".connection-card").count() > 0
        assert await page.locator("body").evaluate("el => el.scrollWidth <= el.clientWidth")
        await page.screenshot(path=ARTIFACTS / "fareweave-results-desktop.png", full_page=True)
        await browser.close()
    print("Browser UI, Kalender, Loader und Viewports: OK")


if __name__ == "__main__":
    asyncio.run(main())
