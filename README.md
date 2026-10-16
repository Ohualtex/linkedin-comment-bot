# LinkedIn Automated Commenting Bot (Generic & Multi-Topic)

A robust, modular, and anti-detection automation tool to find recent LinkedIn content by any keyword or hashtag and post human-like comments using Playwright persistent sessions.

---

## Architecture Overview

```text
linkedin-comment-bot/
├── templates.txt              # Customizable comment templates pool
├── url_builder.py             # Dynamic search query builder (keywords, date, sort)
├── config.py                  # Configuration loader (.env and defaults)
├── storage.py                 # SQLite deduplication & interaction history
├── browser.py                 # Playwright persistent context & stealth manager
├── commenter.py               # Feed navigation, human typing, and duplicate evasion
├── main.py                    # Multi-topic CLI entrypoint
├── requirements.txt           # Python dependencies
├── .env.example               # Example environment configuration
└── README.md                  # Project documentation
```

---

## Features

- **Multi-Topic & Dynamic Querying:** Comment on any hashtag or topic (`--keywords "#python"`, `--keywords "ai, machine learning"`).
- **Flexible Filters:** Filter by date (`--date-posted past-24h|past-week|past-month`) and sort order (`--sort-by date_posted|relevance`).
- **External Template Management:** Easily add or edit comment variations in `templates.txt` or specify a custom template file via `--templates`.
- **Persistent Browser Profile:** Log in manually once; cookies and sessions are safely saved in `./session_data/` so credentials are never hardcoded.
- **2-Tier Duplicate Prevention:**
  1. Local SQLite database (`history.db`) ensures posts commented by the bot are never touched again.
  2. Live DOM checks detect if you manually commented on a post earlier via LinkedIn social proof headers or existing comments in the thread.
- **Human Emulation:**
  - Realistic typing speed (40–120ms randomized delay per character).
  - Jitter delays between posts (12–25 seconds).
  - Bot evasion (`navigator.webdriver = undefined`).
- **Safety Modes:**
  - `--dry-run`: Previews posts and comments without sending anything.
  - `--stats`: Summarizes past activity from the database.

---

## Quick Start

### 1. Installation
```bash
# Activate existing virtual environment
.\.venv\Scripts\Activate.ps1

# (Optional) Ensure dependencies are installed
pip install -r requirements.txt
playwright install chromium
```

### 2. Initial Login (One-Time)
```bash
python main.py --setup-session
```
Log in to LinkedIn in the browser window that opens. Once logged in, your session is saved locally in `./session_data/`.

### 3. Usage Examples

#### Dry-Run Preview (Recommended for Testing)
```bash
python main.py --keywords "#python" --dry-run
```

#### Run for Specific Keywords & Date Range
```bash
python main.py --keywords "#ai, #technology" --date-posted past-week --limit 3
```

#### Custom Comment Text
```bash
python main.py --keywords "#webdev" --comment "Great insight! Thanks for sharing." --limit 2
```

#### Use Custom Templates File
```bash
python main.py --keywords "#datascience" --templates ./my_templates.txt --limit 5
```

#### View Activity Statistics
```bash
python main.py --stats
```

---

## Safety Recommendations

1. **Daily Limits:** Keep `--limit` between 5 and 15 per day to prevent LinkedIn rate limits.
2. **Keep Browser Visible (`HEADLESS=false`):** Allows immediate observation and manual intervention if LinkedIn displays a security check.
3. **Template Diversity:** Maintain at least 5–10 diverse templates in `templates.txt` to avoid repetitive messaging.
