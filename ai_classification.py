"""
ai_classification.py
=====================
An AI-based alternative to classification.py's keyword classifier, using
an agent deployed in Azure AI Foundry.

This deliberately mirrors classify_category()'s signature —
(text: str) -> tuple[Category, float] — so it's a drop-in replacement:
analyzer.py could call either one without anything else in the project
needing to change. That's the same "swap this seam out for AI later"
idea the project notes already called out.

Which model?
------------
The model is NOT chosen in this code. The request goes to a Foundry agent
via agent_reference (name + version from config.py), and the model is
whatever that agent version is configured to use in the Foundry portal.
Saving changes to an agent creates a new version, so switching models
usually also means updating AZURE_AI_AGENT_VERSION. Every call prints the
model that actually answered (response.model) to stderr.

Credentials
-----------
Authentication uses DefaultAzureCredential (Microsoft Entra ID), e.g.
`az login` locally — no API key. The project endpoint, agent name and
agent version come from config.load_config(), which reads them from a
git-ignored .env file (see .env.example).

Requires: pip install "azure-ai-projects>=2.1.0" azure-identity openai
"""

from __future__ import annotations

import json
import sys

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from config import load_config
from models import Category

_SYSTEM_PROMPT = (
    "You are an IT support triage assistant for a Citrix environment. Do not tell the user what you can do. Conversation should be kept to a minimum. "
    "Classify the incident description into exactly one of these "
    f"categories: {', '.join(category.value for category in Category)}. "
    "Respond with ONLY a JSON object of the form "
    '{"category": "<one of the categories above, verbatim>", "confidence": <float 0-1>} '
    "and nothing else. If the text is not an IT incident, still respond with JSON: "
    f'{{"category": "{Category.UNKNOWN.value}", "confidence": 0}}.'
)






def classify_with_ai(text: str) -> tuple[Category, float]:
    config = load_config()

    project_client = AIProjectClient(
        endpoint=config.endpoint,
        credential=DefaultAzureCredential(),
    )
    client = project_client.get_openai_client()

    response = client.responses.create(
    input=[
       {
            "type": "message",
            "role": "developer",
            "content": [
                {
                    "type": "input_text",
                    "text": _SYSTEM_PROMPT,
                }
            ],
        },
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Classify this IT incident. Return only valid JSON "
                        "with the fields category and confidence.\n\n"
                        f"Incident: {text}"
                    ),
                }
            ],
        },
    ],
    extra_body={
        "agent_reference": {
            "name": config.agent_name,
            "version": config.agent_version,
            "type": "agent_reference",
        }
    },
)

    # stderr, so it doesn't mix into the JSON that main.py prints to stdout.
    print(
        f"[ai_classification] agent {config.agent_name} v{config.agent_version} "
        f"answered with model: {response.model}",
        file=sys.stderr,
    )

    raw_output = (response.output_text or "").strip()
    if not raw_output:
        raise RuntimeError(
            "The AI agent returned no text. Check the agent deployment and its "
            "response configuration."
        )

    # Models sometimes wrap an otherwise valid JSON object in Markdown fences.
    if raw_output.startswith("```"):
        lines = raw_output.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_output = "\n".join(lines).strip()

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"The AI agent did not return valid JSON: {raw_output!r}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError("The AI response must be a JSON object")

    try:
        category = Category(parsed["category"])
    except ValueError:
        # The model invented a label that isn't in the list.
        category = Category.UNKNOWN
    confidence = float(parsed["confidence"])

    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")

    return category, confidence