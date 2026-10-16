"""LinkedIn feed traversal and automated commenting logic."""

import logging
import random
import time
from typing import Optional, List, Dict, Any

from playwright.sync_api import Page, Locator

from config import (
    DEFAULT_SEARCH_URL,
    load_templates,
    MIN_DELAY_SECONDS,
    MAX_DELAY_SECONDS,
    MIN_KEYSTROKE_DELAY_MS,
    MAX_KEYSTROKE_DELAY_MS,
)
import storage

logger = logging.getLogger(__name__)


def extract_post_urn(post_locator: Locator) -> Optional[str]:
    """Extracts a unique URN or identifier from a LinkedIn post element."""
    data_urn = post_locator.get_attribute("data-urn") or post_locator.get_attribute("data-id")
    if data_urn and "urn:li:" in data_urn:
        return data_urn

    inner_urn_el = post_locator.locator("[data-urn]").first
    if inner_urn_el.count() > 0:
        val = inner_urn_el.get_attribute("data-urn")
        if val and "urn:li:" in val:
            return val

    activity_link = post_locator.locator("a[href*='/feed/update/urn:li:']").first
    if activity_link.count() > 0:
        href = activity_link.get_attribute("href") or ""
        for part in href.split("/"):
            if part.startswith("urn:li:"):
                return part.split("?")[0]

    return None


def extract_post_url(post_urn: Optional[str], post_locator: Locator) -> str:
    """Builds or extracts the direct URL for a given post."""
    if post_urn and post_urn.startswith("urn:li:"):
        return f"https://www.linkedin.com/feed/update/{post_urn}/"

    permalink_el = post_locator.locator("a[href*='/feed/update/']").first
    if permalink_el.count() > 0:
        href = permalink_el.get_attribute("href")
        if href:
            return href.split("?")[0]

    return ""


def extract_author_name(post_locator: Locator) -> str:
    """Extracts the author or organization name of the post."""
    selectors = [
        ".update-components-actor__name span[aria-hidden='true']",
        ".update-components-actor__name",
        ".feed-shared-actor__name",
        ".update-components-actor__title",
    ]
    for sel in selectors:
        el = post_locator.locator(sel).first
        if el.count() > 0:
            text = el.inner_text().strip()
            if text:
                return text
    return "Unknown Author"


def has_prior_interaction_header(post_locator: Locator) -> bool:
    """Checks whether the post card has a header indicating prior user comment/interaction."""
    header_selectors = [
        ".update-components-header",
        ".feed-shared-header",
        ".update-components-header__text-wrapper",
    ]
    interaction_keywords = [
        "commented on this",
        "buna yorum yaptınız",
        "buna yorum yaptı",
        "you commented",
        "yorum yaptın",
    ]
    for sel in header_selectors:
        header_el = post_locator.locator(sel).first
        if header_el.count() > 0 and header_el.is_visible():
            text = header_el.inner_text().lower()
            for kw in interaction_keywords:
                if kw in text:
                    return True
    return False


def post_has_comment_by_user(post_locator: Locator, user_info: Optional[Dict[str, str]]) -> bool:
    """
    Scans visible comments under this post to detect if the current logged-in user
    has already commented manually.
    """
    if not user_info:
        return False

    target_name = (user_info.get("name") or "").strip().lower()
    target_profile = (user_info.get("profile_url") or "").strip().lower()

    if not target_name and not target_profile:
        return False

    author_locators = post_locator.locator(
        ".comments-comment-item .comments-post-meta__name-text, "
        ".comments-comment-item a[data-field='reply_card_author_name'], "
        ".comments-comment-item a.comments-post-meta__profile-link, "
        ".comments-comment-item .comments-post-meta__profile-link span"
    )

    count = author_locators.count()
    for i in range(count):
        el = author_locators.nth(i)
        try:
            author_text = el.inner_text().strip().lower()
            author_href = (el.get_attribute("href") or "").lower()

            if target_name and target_name in author_text:
                return True
            if target_profile and target_profile in author_href:
                return True
        except Exception:
            continue

    return False


def type_humanlike(locator: Locator, text: str) -> None:
    """Simulates realistic typing with variable keystroke delays."""
    locator.click()
    time.sleep(random.uniform(0.3, 0.7))
    for char in text:
        locator.press_sequentially(
            char,
            delay=random.randint(MIN_KEYSTROKE_DELAY_MS, MAX_KEYSTROKE_DELAY_MS),
        )


def find_comment_button(post_locator: Locator) -> Optional[Locator]:
    """Finds the 'Comment' toggle button in a post card."""
    candidates = [
        post_locator.locator("button[aria-label*='Comment']").first,
        post_locator.locator("button[aria-label*='Yorum']").first,
        post_locator.locator("button.comment-button").first,
        post_locator.locator("button:has-text('Comment')").first,
        post_locator.locator("button:has-text('Yorum')").first,
    ]
    for btn in candidates:
        if btn.count() > 0 and btn.is_visible():
            return btn
    return None


def find_comment_editor(post_locator: Locator) -> Optional[Locator]:
    """Finds the active contenteditable comment box for a post."""
    editor_selectors = [
        "div.ql-editor[contenteditable='true']",
        "div[role='textbox'][contenteditable='true']",
        "div.comments-comment-box-comment__text-editor",
        "div[aria-label*='comment' i][contenteditable='true']",
        "div[aria-label*='yorum' i][contenteditable='true']",
    ]
    for sel in editor_selectors:
        editor = post_locator.locator(sel).first
        if editor.count() > 0 and editor.is_visible():
            return editor
    return None


def find_submit_button(post_locator: Locator) -> Optional[Locator]:
    """Locates the submit button within the comment box."""
    submit_selectors = [
        "button.comments-comment-box__submit-button",
        "button[type='submit']",
        "button:has-text('Post')",
        "button:has-text('Comment')",
        "button:has-text('Yayınla')",
    ]
    for sel in submit_selectors:
        btn = post_locator.locator(sel).first
        if btn.count() > 0 and btn.is_visible() and btn.is_enabled():
            return btn
    return None


def comment_on_feed(
    page: Page,
    search_url: str = DEFAULT_SEARCH_URL,
    max_comments: int = 5,
    dry_run: bool = False,
    custom_comment: Optional[str] = None,
    templates: Optional[List[str]] = None,
    user_info: Optional[Dict[str, str]] = None,
) -> int:
    """
    Navigates to the search URL and iterates through posts to comment automatically.

    Returns:
        Number of successfully commented posts.
    """
    available_templates = templates or load_templates()

    logger.info(f"Navigating to search feed: {search_url}")
    page.goto(search_url, wait_until="domcontentloaded")
    time.sleep(random.uniform(4.0, 7.0))

    success_count = 0
    consecutive_empty_scrolls = 0
    max_empty_scrolls = 5

    logger.info("Scanning for posts in the search results...")

    while success_count < max_comments and consecutive_empty_scrolls < max_empty_scrolls:
        posts = page.locator(".feed-shared-update-v2, div[data-urn*='urn:li:activity:']")
        total_found = posts.count()

        if total_found == 0:
            logger.warning("No post cards found on current view. Scrolling...")
            page.mouse.wheel(0, 1000)
            time.sleep(3)
            consecutive_empty_scrolls += 1
            continue

        action_taken_in_this_pass = False

        for i in range(total_found):
            if success_count >= max_comments:
                break

            post = posts.nth(i)
            try:
                post.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                continue

            urn = extract_post_urn(post)
            if not urn:
                continue

            # 1. Local SQLite deduplication check
            if storage.is_post_commented(urn):
                logger.debug(f"Skipping already recorded post in database: {urn}")
                continue

            author = extract_author_name(post)
            post_url = extract_post_url(urn, post)

            # 2. LinkedIn social proof header check (e.g. "You commented on this")
            if has_prior_interaction_header(post):
                logger.info(
                    f"Skipping post {urn} - Social header indicates you already commented on this post."
                )
                storage.record_comment(
                    post_urn=urn,
                    post_url=post_url,
                    comment_text="[Skipped: Detected prior comment in header]",
                    author=author,
                )
                continue

            logger.info(f"Targeting post: {urn} | Author: {author}")

            # Find comment toggle button
            comment_btn = find_comment_button(post)
            editor = find_comment_editor(post)

            # If editor is not visible yet, click the Comment button to expand it
            if not editor and comment_btn:
                try:
                    comment_btn.click()
                    time.sleep(random.uniform(1.2, 2.0))
                    editor = find_comment_editor(post)
                except Exception as e:
                    logger.warning(f"Could not click comment button: {e}")
                    continue

            # 3. Check if current user's comment is already present in the opened comments thread
            if post_has_comment_by_user(post, user_info):
                logger.info(
                    f"Skipping post {urn} - Found an existing comment by you in the thread."
                )
                storage.record_comment(
                    post_urn=urn,
                    post_url=post_url,
                    comment_text="[Skipped: Detected existing user comment in thread]",
                    author=author,
                )
                continue

            if not editor:
                logger.warning(f"Comment editor could not be located for post: {urn}")
                continue

            # Pick or format comment text
            comment_text = custom_comment or random.choice(available_templates)

            if dry_run:
                print("\n" + "-" * 50)
                print(f" [DRY-RUN PREVIEW]")
                print(f" Post URN : {urn}")
                print(f" Author   : {author}")
                print(f" URL      : {post_url}")
                print(f" Comment  : \"{comment_text}\"")
                print("-" * 50 + "\n")
                success_count += 1
                action_taken_in_this_pass = True
                time.sleep(random.uniform(1.5, 3.0))
                continue

            # Live run: type comment text
            try:
                type_humanlike(editor, comment_text)
                time.sleep(random.uniform(1.0, 2.0))

                submit_btn = find_submit_button(post)
                if not submit_btn:
                    logger.error(f"Submit button not clickable for post: {urn}")
                    continue

                submit_btn.click()
                time.sleep(random.uniform(2.5, 4.0))

                storage.record_comment(
                    post_urn=urn,
                    post_url=post_url,
                    comment_text=comment_text,
                    author=author,
                )
                success_count += 1
                action_taken_in_this_pass = True
                logger.info(f"Successfully posted comment on {urn} ({success_count}/{max_comments})")

                delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                logger.info(f"Sleeping for {delay:.1f}s to maintain natural pace...")
                time.sleep(delay)

            except Exception as exc:
                logger.error(f"Failed to post comment on {urn}: {exc}")
                continue

        if action_taken_in_this_pass:
            consecutive_empty_scrolls = 0
        else:
            consecutive_empty_scrolls += 1

        logger.debug("Scrolling down to load additional feed posts...")
        page.mouse.wheel(0, 1200)
        time.sleep(random.uniform(2.5, 4.5))

    logger.info(f"Finished execution. Total comments posted: {success_count}")
    return success_count
