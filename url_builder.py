"""URL builder module for dynamic LinkedIn content search queries."""

from urllib.parse import quote

BASE_SEARCH_URL = "https://www.linkedin.com/search/results/content/"

VALID_DATE_FILTERS = {
    "past-24h": '["past-24h"]',
    "past-week": '["past-week"]',
    "past-month": '["past-month"]',
}

VALID_SORT_ORDERS = {
    "date_posted": '["date_posted"]',
    "relevance": '["relevance"]',
}


def build_search_url(
    keywords: str = "#python",
    sort_by: str = "date_posted",
    date_posted: str = "past-week",
) -> str:
    """
    Builds a LinkedIn content search URL with proper faceted search filters.

    Args:
        keywords: Search query (e.g., "#python", "machine learning", "#webdev")
        sort_by: "date_posted" (newest first) or "relevance"
        date_posted: "past-24h", "past-week", or "past-month"

    Returns:
        Full formatted LinkedIn search URL.
    """
    cleaned_keywords = keywords.strip()
    if not cleaned_keywords:
        cleaned_keywords = "#tech"

    # Resolve date filter
    date_val = VALID_DATE_FILTERS.get(date_posted.lower().strip(), '["past-week"]')

    # Resolve sort filter
    sort_val = VALID_SORT_ORDERS.get(sort_by.lower().strip(), '["date_posted"]')

    # Manually construct query params to match LinkedIn's faceted JSON formatting
    encoded_keywords = quote(cleaned_keywords)
    encoded_sort = quote(sort_val)
    encoded_date = quote(date_val)

    url = (
        f"{BASE_SEARCH_URL}?"
        f"keywords={encoded_keywords}&"
        f"origin=FACETED_SEARCH&"
        f"sortBy={encoded_sort}&"
        f"datePosted={encoded_date}"
    )
    return url
