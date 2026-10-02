from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Category(str, Enum):
    AUTHENTICATION = "Authentication / Login"
    SESSION = "Session / ICA Connection"
    PERFORMANCE = "Performance / Slowness"
    PRINTING = "Printing"
    APPLICATION = "Application / Published App"
    LICENSING = "Licensing"
    NETWORK = "Network / Connectivity"
    STOREFRONT = "StoreFront / Gateway"
    PROFILE = "User Profile"
    UNKNOWN = "Uncategorized"


class Priority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class Incident:
    """Raw incident as submitted, e.g. from a ticketing system or a form."""

    incident_id: str
    description: str
    reported_by: Optional[str] = None
    reported_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    affected_system: Optional[str] = None  # e.g. hostname, farm, or app name


@dataclass
class ExtractedInfo:
    """Facts pulled out of the description by extraction.py."""

    error_codes: list[str]
    affected_users_count: Optional[int]


@dataclass
class Classification:
    """What kind of problem it is, how urgent, and how sure we are."""

    category: Category
    priority: Priority
    confidence: float


@dataclass
class AnalysisResult:
    """Structured output of analyzer.analyze_incident()."""

    incident: Incident
    extracted: ExtractedInfo
    classification: Classification

    def to_dict(self) -> dict:
        """Flatten into the JSON-ready shape the app has always printed."""
        return {
            "incident_id": self.incident.incident_id,
            "reported_by": self.incident.reported_by,
            "reported_at": self.incident.reported_at,
            "affected_system": self.incident.affected_system,
            "original_description": self.incident.description,
            "extracted": {
                "error_codes": self.extracted.error_codes,
                "affected_users_count": self.extracted.affected_users_count,
            },
            "classification": {
                "category": self.classification.category.value,
                "priority": self.classification.priority.value,
                "confidence": self.classification.confidence,
            },
        }


@dataclass
class Solution:
    """The solution agent's answer and the Citrix docs it cited."""

    answer: str
    sources: list[str] = field(default_factory=list)  # doc URLs


@dataclass
class IncidentResponse:
    """Final output of the orchestrator workflow for a new incident."""

    analysis: AnalysisResult
    solution: Solution