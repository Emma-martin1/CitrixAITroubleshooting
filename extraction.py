from __future__ import annotations

import re
from typing import Optional

from models import Priority

# Matches things like "Error 1030", "error #1105", "SF-1101", "0x80090326"
ERROR_CODE_PATTERN = re.compile(
    r"\b(?:error\s*#?\s*)?(\d{3,5}|0x[0-9a-fA-F]{4,8}|SF-\d{3,5})\b",
    re.IGNORECASE,
)

# Matches phrases like "affecting 15 users" or "200 users impacted"
AFFECTED_USERS_PATTERN = re.compile(r"(\d+)\s+users?", re.IGNORECASE)

# Keywords that hint at how urgent an incident is, ordered from most to
# least severe. Checked in this order so "critical" wins over "slow" if a
# description happens to mention both.
PRIORITY_KEYWORDS: dict[Priority, list[str]] = {
    Priority.CRITICAL: ["critical", "urgent", "down", "outage", "all users", "emergency"],
    Priority.HIGH: ["cannot work", "blocked", "asap", "many users", "several users"],
    Priority.MEDIUM: ["slow", "intermittent", "delay", "sluggish"],
    Priority.LOW: ["minor", "cosmetic", "when possible", "low priority"],
}


def extract_error_codes(text: str) -> list[str]:
    """Return the distinct error codes mentioned in the text, if any."""
    return sorted({match.group(0) for match in ERROR_CODE_PATTERN.finditer(text)})


def extract_affected_users_count(text: str) -> Optional[int]:
    """Return the number of affected users mentioned in the text, if any."""
    match = AFFECTED_USERS_PATTERN.search(text)
    return int(match.group(1)) if match else None


def extract_priority(text: str) -> Priority:
    """Guess a priority from urgency-related keywords, defaulting to Medium."""
    lowered = text.lower()
    for priority in (Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW):
        if any(keyword in lowered for keyword in PRIORITY_KEYWORDS[priority]):
            return priority
    return Priority.MEDIUM
