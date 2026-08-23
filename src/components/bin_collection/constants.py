"""Constants for the Waltham Forest bin-collection scrape.

This isn't a standalone summary/full-screen component - it just supplies
synthetic calendar-like entries that `google_calendar` merges into its own
rendering, so the only configuration here is what the scrape itself needs.
"""

import datetime

FORM_URL = (
    "https://portal.walthamforest.gov.uk/AchieveForms/"
    "?mode=fill&consentMessage=yes"
    "&form_uri=sandbox-publish://AF-Process-d62ccdd2-3de9-48eb-a229-8e20cbdd6393"
    "/AF-Stage-8bf39bf9-5391-4c24-857f-0dc2025c67f4/definition.json"
    "&process=1"
    "&process_uri=sandbox-processes://AF-Process-d62ccdd2-3de9-48eb-a229-8e20cbdd6393"
    "&process_id=AF-Process-d62ccdd2-3de9-48eb-a229-8e20cbdd6393"
)

# The site only ever exposes the *next* collection date per waste stream, not
# a full recurring schedule, so a scrape every few days is all a 3-day
# collection cadence needs.
CACHE_LIFETIME = datetime.timedelta(days=3)

PAGE_LOAD_TIMEOUT_MS = 30_000
RESULT_TIMEOUT_MS = 30_000

# Maps the site's own service names to the short labels requested for the
# calendar ("Food, Recycling, Refuse" rather than the full service names).
_CATEGORY_KEYWORDS: dict[str, str] = {
    "food": "Food",
    "garden": "Garden",
    "recycling": "Recycling",
}
DEFAULT_CATEGORY = "Refuse"  # "Domestic Waste Collection Service" and similar


def short_category_name(service_name: str) -> str:
    """Map a full service name (e.g. "Food Waste Collection Service") to the
    short label used on the calendar.
    """
    lowered = service_name.lower()
    for keyword, label in _CATEGORY_KEYWORDS.items():
        if keyword in lowered:
            return label
    return DEFAULT_CATEGORY
