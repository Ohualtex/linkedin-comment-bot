"""Browser management and persistent session module using Playwright."""

import logging
import time
from pathlib import Path
from typing import Optional, List, Dict
from contextlib import contextmanager

from playwright.sync_api import sync_playwright, BrowserContext, Page

from config import BROWSER_USER_DATA_DIR, HEADLESS

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def get_browser_args() -> list[str]:
    """Returns chromium launch arguments designed to minimize bot detection."""
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-first-run",
        "--no-service-autorun",
        "--password-store=basic",
    ]


@contextmanager
def launch_browser(
    user_data_dir: Optional[Path] = None,
    headless: Optional[bool] = None,
) -> BrowserContext:
    """Launches Chromium with persistent user profile and anti-detection settings."""
    profile_dir = Path(user_data_dir or BROWSER_USER_DATA_DIR)
    profile_dir.mkdir(parents=True, exist_ok=True)
    is_headless = HEADLESS if headless is None else headless

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=is_headless,
            viewport={"width": 1366, "height": 768},
            user_agent=DEFAULT_USER_AGENT,
            args=get_browser_args(),
            locale="en-US",
        )

        # Evade navigator.webdriver detection
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """
        )

        try:
            yield context
        finally:
            context.close()


def is_logged_in(page: Page) -> bool:
    """Checks whether the current session has an active LinkedIn login."""
    try:
        current_url = page.url.lower()
        if "login" in current_url or "checkpoint" in current_url or "signup" in current_url:
            return False

        nav = page.locator(".global-nav, #global-nav, input.search-global-typeahead__input")
        if nav.count() > 0:
            return True

        cookies = page.context.cookies(["https://www.linkedin.com"])
        for cookie in cookies:
            if cookie.get("name") == "li_at":
                return True

        return False
    except Exception as exc:
        logger.debug(f"Error checking login state: {exc}")
        return False


def wait_for_manual_login(page: Page, timeout_seconds: int = 300) -> bool:
    """Guides the user through manual login if no active session is found."""
    logger.info("Navigating to LinkedIn login page...")
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

    if is_logged_in(page):
        logger.info("Active session detected! Already logged in.")
        return True

    print("\n" + "=" * 60)
    print(" [ATTENTION REQUIRED] LinkedIn Login")
    print(" Please log in using the open browser window.")
    print(" Complete any 2FA or security verification if prompted.")
    print(" Once logged in and on the feed, this script will continue.")
    print("=" * 60 + "\n")

    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if is_logged_in(page) or "feed" in page.url.lower():
            logger.info("Login successfully completed and verified!")
            time.sleep(3)
            return True
        time.sleep(2)

    logger.error("Login timed out.")
    return False


def get_logged_in_user_info(page: Page) -> Dict[str, str]:
    """
    Extracts the logged-in user's name and profile identifier from the LinkedIn DOM.
    Returns:
        dict: {"name": str, "profile_url": str}
    """
    info = {"name": "", "profile_url": ""}
    try:
        # 1. Profile image alt text in global navigation bar
        me_photo = page.locator("img.global-nav__me-photo, .global-nav__primary-link-me img").first
        if me_photo.count() > 0:
            alt = me_photo.get_attribute("alt")
            if alt and alt.strip():
                clean_name = (
                    alt.replace("Photo of", "")
                    .replace("Fotoğrafı", "")
                    .replace("profile picture", "")
                    .strip()
                )
                if clean_name:
                    info["name"] = clean_name

        # 2. Feed identity module link on left sidebar
        feed_profile = page.locator(
            ".feed-identity-module__actor-meta a, a.feed-identity-module__name, .identity-headline a"
        ).first
        if feed_profile.count() > 0:
            href = feed_profile.get_attribute("href") or ""
            if "/in/" in href:
                info["profile_url"] = href.split("?")[0]
            if not info["name"]:
                text = feed_profile.inner_text().strip()
                if text:
                    info["name"] = text

        # 3. Check me button or dropdown text
        if not info["name"]:
            me_btn = page.locator(".global-nav__primary-link-me").first
            if me_btn.count() > 0:
                text = me_btn.inner_text().strip()
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                for line in lines:
                    if line.lower() not in ("me", "ben"):
                        info["name"] = line
                        break

    except Exception as exc:
        logger.debug(f"Could not extract user info: {exc}")

    if info["name"]:
        logger.info(f"Detected logged-in user: '{info['name']}' (Profile: {info['profile_url'] or 'N/A'})")
    return info
