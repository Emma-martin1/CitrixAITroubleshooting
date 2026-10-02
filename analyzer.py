"""
analyzer.py
===========
Combines extraction + classification into an AnalysisResult (see
models.py), which can be turned into JSON at the very end. This is the
"service layer": the one function other
code (main.py, a future test suite, a future web app) calls to turn an
Incident into an answer, without needing to know how extraction or
classification work internally.
"""

from __future__ import annotations

import json

##from classification import classify_category
from ai_classification import classify_with_ai
from extraction import extract_affected_users_count, extract_error_codes, extract_priority
from models import AnalysisResult, Classification, ExtractedInfo, Incident




def analyze_incident(incident: Incident) -> AnalysisResult:
    """Run extraction + classification on an Incident and return an AnalysisResult."""
    text = incident.description
    ##category, confidence = classify_category(text)
    category, confidence = classify_with_ai(text)

    return AnalysisResult(
        incident=incident,
        extracted=ExtractedInfo(
            error_codes=extract_error_codes(text),
            affected_users_count=extract_affected_users_count(text),
        ),
        classification=Classification(
            category=category,
            priority=extract_priority(text),
            confidence=confidence,
        ),
    )


def analyze_incident_to_json(incident: Incident, indent: int = 2) -> str:
    """Convenience wrapper: same as analyze_incident() but as a JSON string."""
    return json.dumps(analyze_incident(incident).to_dict(), indent=indent)
