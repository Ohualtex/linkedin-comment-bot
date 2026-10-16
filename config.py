"""Configuration module for generic LinkedIn automated commenting bot."""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from url_builder import build_search_url

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file if present
load_dotenv(BASE_DIR / ".env")

# Search query parameters
LINKEDIN_KEYWORDS = os.getenv("LINKEDIN_KEYWORDS", "#python")
LINKEDIN_SORT_BY = os.getenv("LINKEDIN_SORT_BY", "date_posted")
LINKEDIN_DATE_POSTED = os.getenv("LINKEDIN_DATE_POSTED", "past-week")

# Custom search URL override (if specified, takes priority over builder)
CUSTOM_SEARCH_URL = os.getenv("LINKEDIN_CUSTOM_SEARCH_URL", "").strip()

DEFAULT_SEARCH_URL = CUSTOM_SEARCH_URL or build_search_url(
    keywords=LINKEDIN_KEYWORDS,
    sort_by=LINKEDIN_SORT_BY,
    date_posted=LINKEDIN_DATE_POSTED,
)

# Template file path
TEMPLATES_FILE = Path(os.getenv("TEMPLATES_FILE", BASE_DIR / "templates.txt")).resolve()


def load_templates(filepath: Path = TEMPLATES_FILE) -> List[str]:
    """Loads comment templates from a file, ignoring comments (#) and blank lines."""
    if not filepath.exists():
        return [
            "Great insights! Thanks for sharing. 👏",
            "Very informative post. Keep up the great work! 🚀",
            "Impressive update! Best of luck with the next milestones.",
        ]

    with open(filepath, "r", encoding="utf-8") as f:
        lines = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    return lines if lines else ["Great share! Thanks for posting. 👏"]


# Browser session directory for persistent context (keeps you logged in)
BROWSER_USER_DATA_DIR = Path(
    os.getenv("BROWSER_USER_DATA_DIR", BASE_DIR / "session_data")
).resolve()

# Execution settings
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")
MAX_COMMENTS_PER_RUN = int(os.getenv("MAX_COMMENTS_PER_RUN", "5"))

# Anti-detection & jitter delay range (in seconds)
MIN_DELAY_SECONDS = int(os.getenv("MIN_DELAY_SECONDS", "12"))
MAX_DELAY_SECONDS = int(os.getenv("MAX_DELAY_SECONDS", "25"))

# Typing simulation delays (in milliseconds per character)
MIN_KEYSTROKE_DELAY_MS = 40
MAX_KEYSTROKE_DELAY_MS = 120

# SQLite database for deduplication
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "history.db")).resolve()
