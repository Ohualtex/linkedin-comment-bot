"""CLI entry point for generic LinkedIn automated commenting tool."""

import argparse
import logging
import sys
from pathlib import Path

import config
import storage
from url_builder import build_search_url, VALID_DATE_FILTERS, VALID_SORT_ORDERS
from browser import (
    launch_browser,
    is_logged_in,
    wait_for_manual_login,
    get_logged_in_user_info,
)
from commenter import comment_on_feed

# Configure console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def print_banner() -> None:
    """Prints the application banner."""
    print("=" * 68)
    print("      LinkedIn Automated Commenting Tool (Generic / Multi-Topic)    ")
    print("=" * 68)


def show_statistics() -> None:
    """Displays stats about past commented posts from SQLite."""
    print_banner()
    total = storage.get_commented_count()
    print(f"\n Total commented posts in database: {total}")

    if total > 0:
        print("\n Most recent 5 commented posts:")
        print("-" * 68)
        recent = storage.get_recent_comments(limit=5)
        for r in recent:
            print(f" Date    : {r['commented_at']}")
            print(f" Author  : {r['author']}")
            print(f" URN     : {r['post_urn']}")
            print(f" Comment : {r['comment_text']}")
            print("-" * 68)
    print()


def parse_arguments() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generic automated LinkedIn commenting script for any topic or hashtag."
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default=config.LINKEDIN_KEYWORDS,
        help=f"Keywords or hashtag to search (default: '{config.LINKEDIN_KEYWORDS}').",
    )
    parser.add_argument(
        "--date-posted",
        type=str,
        default=config.LINKEDIN_DATE_POSTED,
        choices=list(VALID_DATE_FILTERS.keys()),
        help=f"Date filter: past-24h, past-week, or past-month (default: '{config.LINKEDIN_DATE_POSTED}').",
    )
    parser.add_argument(
        "--sort-by",
        type=str,
        default=config.LINKEDIN_SORT_BY,
        choices=list(VALID_SORT_ORDERS.keys()),
        help=f"Sort order: date_posted (newest) or relevance (default: '{config.LINKEDIN_SORT_BY}').",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Direct custom search URL override (bypasses keyword builder).",
    )
    parser.add_argument(
        "--templates",
        type=str,
        default=None,
        help="Path to a custom comment templates text file.",
    )
    parser.add_argument(
        "--comment",
        type=str,
        default=None,
        help="Specific comment string to use instead of template file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=config.MAX_COMMENTS_PER_RUN,
        help=f"Maximum posts to comment on (default: {config.MAX_COMMENTS_PER_RUN}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution and preview posts/comments without submitting.",
    )
    parser.add_argument(
        "--setup-session",
        action="store_true",
        help="Launch browser to manually log in to LinkedIn and save persistent session.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Display statistics of previously commented posts.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (headless=false recommended for safety).",
    )
    return parser.parse_args()


def main() -> None:
    """Main execution workflow."""
    args = parse_arguments()

    if args.stats:
        show_statistics()
        return

    print_banner()
    logger.info("Initializing database...")
    storage.init_db()

    headless_mode = args.headless or config.HEADLESS

    # Setup session mode
    if args.setup_session:
        logger.info("Starting interactive session setup mode...")
        with launch_browser(headless=False) as context:
            page = context.new_page()
            success = wait_for_manual_login(page)
            if success:
                logger.info("Session saved successfully! You can now run the script normally.")
            else:
                logger.error("Session setup failed or was aborted.")
        return

    # Determine target URL
    if args.url:
        target_url = args.url
    else:
        target_url = build_search_url(
            keywords=args.keywords,
            sort_by=args.sort_by,
            date_posted=args.date_posted,
        )

    # Determine templates
    if args.templates:
        template_file = Path(args.templates).resolve()
        templates_pool = config.load_templates(template_file)
    else:
        templates_pool = config.load_templates()

    logger.info(f"Target Keywords : {args.keywords}")
    logger.info(f"Target URL      : {target_url}")
    logger.info(f"Templates Loaded: {len(templates_pool)} available")
    logger.info(f"Limit           : {args.limit} posts")
    logger.info(f"Dry-run Mode    : {args.dry_run}")
    logger.info(f"Headless Mode   : {headless_mode}")

    with launch_browser(headless=headless_mode) as context:
        page = context.new_page()

        # Step 1: Verify authentication
        logger.info("Checking LinkedIn authentication...")
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")

        if not is_logged_in(page):
            logger.warning("No active session detected!")
            if headless_mode:
                logger.error(
                    "Cannot log in automatically in headless mode. "
                    "Run with '--setup-session' first to log in manually."
                )
                sys.exit(1)

            logged_in = wait_for_manual_login(page)
            if not logged_in:
                logger.error("Authentication could not be established. Exiting.")
                sys.exit(1)

        logger.info("Authentication verified.")

        # Step 2: Fetch current user info for prior-comment detection
        user_info = get_logged_in_user_info(page)

        # Step 3: Feed traversal and commenting
        count = comment_on_feed(
            page=page,
            search_url=target_url,
            max_comments=args.limit,
            dry_run=args.dry_run,
            custom_comment=args.comment,
            templates=templates_pool,
            user_info=user_info,
        )

        logger.info(f"Execution completed. Total actions: {count}")


if __name__ == "__main__":
    main()
