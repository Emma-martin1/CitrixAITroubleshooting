"""
create_solution_agent.py
========================
Creates (or adds a new version of) the "citrix-solution-agent" in Foundry:
a prompt agent with the File Search tool bound to the "citrix-docs" vector
store. It uses the same model as the classifier agent's configured version.

Foundry creates a new agent version every time this runs. The script prints
the version number; the app uses AZURE_AI_SOLUTION_AGENT_VERSION from .env,
so update that when you create a newer version.

Run from the project root (after scripts/build_vector_store.py):
    python scripts/create_solution_agent.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import VECTOR_STORE_NAME, load_config  # noqa: E402

INSTRUCTIONS = """\
You are a Citrix support engineer helping an IT user fix an incident.

The first message contains a JSON analysis of the incident produced by a
classification agent: category, priority, confidence, extracted error codes,
affected user count, and the original description. Later messages are
follow-up questions about the same incident.

How to answer:
- Search the Citrix documentation with the file search tool before answering.
  Base your answer on what the documentation says; do not invent settings,
  policy names, registry keys or commands.
- Use the classification as a hint, not a fact. If the description points to
  a different area than the category, say so and follow the description.
- Reason step by step about the most likely causes, then give numbered
  troubleshooting steps, most likely / least disruptive first.
- If the documentation does not cover the problem, say that clearly and give
  general next steps (logs to check, information to collect).
- If key information is missing, ask one short clarifying question at the end.
- If the message is not about an IT or Citrix problem, say briefly that you can
  only help with Citrix incidents.
- Be concise and friendly. The answer is shown in a plain terminal, so write
  plain text only: no Markdown (no #, ** or tables). Short numbered lists are fine.
- Do not add a "Sources" or "Reference" section, and do not list URLs or
  document names — the app adds the cited sources itself.
"""


def find_vector_store_id(client) -> str:
    for store in client.vector_stores.list():
        if store.name == VECTOR_STORE_NAME:
            return store.id
    raise SystemExit(
        f"Vector store '{VECTOR_STORE_NAME}' not found. Run scripts/build_vector_store.py first."
    )


def main() -> None:
    config = load_config()
    project_client = AIProjectClient(endpoint=config.endpoint, credential=DefaultAzureCredential())
    vector_store_id = find_vector_store_id(project_client.get_openai_client())

    classifier = project_client.agents.get_version(
        agent_name=config.agent_name, agent_version=config.agent_version
    )
    model = classifier.definition["model"]

    agent = project_client.agents.create_version(
        agent_name=config.solution_agent_name,
        description="Finds Citrix troubleshooting steps in the citrix-docs vector store.",
        definition=PromptAgentDefinition(
            model=model,
            instructions=INSTRUCTIONS,
            tools=[FileSearchTool(vector_store_ids=[vector_store_id])],
        ),
    )

    print(f"Created agent '{agent.name}' version {agent.version} (model: {model}, vector store: {vector_store_id})")
    if agent.version != config.solution_agent_version:
        print(
            f"Note: the app is set to use version {config.solution_agent_version}. "
            f"Set AZURE_AI_SOLUTION_AGENT_VERSION={agent.version} in .env."
        )


if __name__ == "__main__":
    main()
