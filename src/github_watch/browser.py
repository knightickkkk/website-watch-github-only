from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib

from playwright.async_api import async_playwright

from .issues import WatchRequest


@dataclass(slots=True)
class Capture:
    title: str
    final_url: str
    tracked_text: str
    text_hash: str
    screenshot_hash: str
    screenshot_path: Path


async def capture_request(request: WatchRequest, screenshot_dir: Path) -> Capture:
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = screenshot_dir / f"{request.key}.png"

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 1365, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        try:
            response = await page.goto(request.website, wait_until="domcontentloaded", timeout=30000)
            if response and response.status >= 400:
                raise RuntimeError(f"HTTP {response.status} while loading {request.website}")

            await page.wait_for_timeout(1500)
            await _remove_common_noise(page)
            tracked_text = await _tracked_text(page, request.selector)
            title = await page.title()
            await page.screenshot(path=str(screenshot_path), full_page=True)

            return Capture(
                title=title,
                final_url=page.url,
                tracked_text=tracked_text,
                text_hash=_sha256_text(tracked_text),
                screenshot_hash=_sha256_file(screenshot_path),
                screenshot_path=screenshot_path,
            )
        finally:
            await browser.close()


async def _remove_common_noise(page) -> None:
    for selector in ("script", "style", "noscript"):
        try:
            await page.locator(selector).evaluate_all(
                "(elements) => elements.forEach((element) => element.remove())"
            )
        except Exception:
            continue


async def _tracked_text(page, selector: str) -> str:
    if selector.strip():
        try:
            texts = await page.locator(selector).all_inner_texts()
            return _normalize_text(" | ".join(texts)) if texts else "<selector matched no text>"
        except Exception as exc:
            return f"<selector error: {exc}>"

    text = await page.evaluate(
        "() => document.body ? document.body.innerText : document.documentElement.innerText"
    )
    return _normalize_text(str(text))


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
