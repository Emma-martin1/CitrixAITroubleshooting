from __future__ import annotations

import argparse
import asyncio
import itertools
import json

from models import Incident, Solution
from orchestrator import CitrixHelper

# A simple in-memory counter for incident IDs (INC-0001, INC-0002, ...).
# Resets every time the program restarts — fine for a demo, but a real
# system would get IDs from a database or ticketing system instead.
_incident_counter = itertools.count(1)

HELP = "Type a follow-up question, 'new' for a new incident, or 'quit' to exit."


def next_incident_id() -> str:
    return f"INC-{next(_incident_counter):04d}"


def prompt_for_incident() -> Incident:
    """Ask the user a couple of questions and build an Incident from the answers."""
    description = input("Describe the incident: ").strip()

    while not description:
        print("A description is required.")
        description = input("Describe the incident: ").strip()

    reported_by = input("Reported by (optional, press Enter to skip): ").strip() or None

    return Incident(
        incident_id=next_incident_id(),
        description=description,
        reported_by=reported_by,
    )


def print_solution(solution: Solution) -> None:
    print()
    print(solution.answer)
    if solution.sources:
        print("\nSources:")
        for url in solution.sources:
            print(f"  - {url}")
    print()


async def chat(show_json: bool) -> None:
    helper = CitrixHelper()
    print("=== Citrix Helper ===")

    while True:
        incident = prompt_for_incident()
        print("\nAnalysing the incident and searching the Citrix docs...")
        response = await helper.new_incident(incident)

        classification = response.analysis.classification
        print(
            f"\n[{incident.incident_id}] Category: {classification.category.value}"
            f" | Priority: {classification.priority.value}"
            f" | Confidence: {classification.confidence:.0%}"
        )
        if show_json:
            print(json.dumps(response.analysis.to_dict(), indent=2))
        print_solution(response.solution)

        print(HELP)
        while True:
            text = input("You: ").strip()
            if not text:
                continue
            if text.lower() in ("quit", "exit"):
                return
            if text.lower() == "new":
                print()
                break
            print_solution(await helper.follow_up(text))


def main() -> None:
    parser = argparse.ArgumentParser(description="Citrix incident helper")
    parser.add_argument("--json", action="store_true", help="also print the classification JSON")
    args = parser.parse_args()

    try:
        asyncio.run(chat(show_json=args.json))
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
