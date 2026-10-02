"""
Configuration for the Foundry project and agents.

Values come from environment variables, loaded from a local .env file
(git-ignored; copy .env.example to get started). Authentication itself uses
Microsoft Entra ID via DefaultAzureCredential, so no API key is stored anywhere.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Foundry vector store holding docs/citrix (see scripts/build_vector_store.py).
VECTOR_STORE_NAME = "citrix-docs"


@dataclass(frozen=True)
class FoundryConfig:
    endpoint: str
    # Classifier agent
    agent_name: str
    agent_version: str
    # RAG solution agent (see scripts/create_solution_agent.py)
    solution_agent_name: str
    solution_agent_version: str


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name} (set it in .env — see .env.example)"
        )
    return value


def load_config() -> FoundryConfig:
    return FoundryConfig(
        endpoint=_required("AZURE_AI_PROJECT_ENDPOINT"),
        agent_name=_required("AZURE_AI_AGENT_NAME"),
        agent_version=os.getenv("AZURE_AI_AGENT_VERSION", "1"),
        solution_agent_name=os.getenv("AZURE_AI_SOLUTION_AGENT_NAME", "citrix-solution-agent"),
        solution_agent_version=os.getenv("AZURE_AI_SOLUTION_AGENT_VERSION", "1"),
    )
