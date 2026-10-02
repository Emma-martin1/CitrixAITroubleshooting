from __future__ import annotations

from models import Category

# Keywords that suggest which part of the Citrix stack is involved.
CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.AUTHENTICATION: [
        "login", "log in", "password", "authentication", "mfa", "2fa",
        "credentials", "locked out",
    ],
    Category.SESSION: [
        "ica", "session", "disconnect", "black screen", "freeze", "frozen",
        "reconnect",
    ],
    Category.PERFORMANCE: [
        "slow", "lag", "latency", "high cpu", "performance", "hang",
    ],
    Category.PRINTING: [
        "print", "printer", "spooler", "pdf print",
    ],
    Category.APPLICATION: [
        "application", "app crash", "published app", "excel", "outlook",
        "crash",
    ],
    Category.LICENSING: [
        "license", "licensing", "no license", "license server",
    ],
    Category.NETWORK: [
        "network", "vpn", "connectivity", "timeout", "dns", "packet loss",
    ],
    Category.STOREFRONT: [
        "storefront", "gateway", "netscaler", "adc", "citrix workspace app",
        "receiver",
    ],
    Category.PROFILE: [
        "profile", "upm", "roaming profile", "corrupt profile",
    ],
}


def classify_category(text: str) -> tuple[Category, float]:
    """
    Score each category by how many of its keywords appear in the text,
    and return the best match plus a simple confidence score (0-1) based
    on how dominant that match was relative to the others.
    """
    lowered = text.lower()
    scores: dict[Category, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in lowered)
        if hits:
            scores[category] = hits

    if not scores:
        return Category.UNKNOWN, 0.0

    best_category = max(scores, key=scores.get)
    total_hits = sum(scores.values())
    confidence = round(scores[best_category] / total_hits, 2)
    return best_category, confidence
