"""
orchestrator.py
===============
Multi-agent orchestration with Microsoft Agent Framework.

A new incident runs through a two-step workflow:

    Incident ─► ClassifyExecutor ─► AnalysisResult ─► SolveExecutor ─► IncidentResponse
                (classifier agent +                    (solution agent + File Search
                 regex extraction)                      over the citrix-docs vector store)

Follow-up questions skip the workflow and go straight to the solution agent
in the same session, so it remembers the incident and its earlier answer.

Note: no `from __future__ import annotations` here — Agent Framework reads the
@handler type hints at runtime to route messages between executors.
"""

import asyncio
import json
from pathlib import Path
from typing import Never

from agent_framework import AgentResponse, AgentSession, Executor, WorkflowBuilder, WorkflowContext, handler
from agent_framework.foundry import FoundryAgent
from azure.identity import DefaultAzureCredential

from analyzer import analyze_incident
from config import load_config
from models import AnalysisResult, Incident, IncidentResponse, Solution

DOCS_DIR = Path(__file__).resolve().parent / "docs" / "citrix"


def _load_source_urls() -> dict[str, str]:
    """Map each uploaded doc's file name to the 'Source:' URL on its first line.

    File Search citations only carry the uploaded file name, so this turns
    them back into links the user can open.
    """
    urls = {}
    for path in DOCS_DIR.rglob("*.md"):
        with path.open(encoding="utf-8") as f:
            first_line = f.readline().strip()
        if first_line.startswith("Source:"):
            urls[path.name] = first_line.removeprefix("Source:").strip()
    return urls


class ClassifyExecutor(Executor):
    """Step 1: classify the incident (Foundry classifier agent + regex extraction)."""

    def __init__(self) -> None:
        super().__init__(id="classify")

    @handler
    async def classify(self, incident: Incident, ctx: WorkflowContext[AnalysisResult]) -> None:
        # analyze_incident() makes a blocking network call; keep the event loop free.
        result = await asyncio.to_thread(analyze_incident, incident)
        await ctx.send_message(result)


class SolveExecutor(Executor):
    """Step 2: hand the classification JSON to the RAG solution agent."""

    def __init__(self, helper: "CitrixHelper") -> None:
        super().__init__(id="solve")
        self._helper = helper

    @handler
    async def solve(self, analysis: AnalysisResult, ctx: WorkflowContext[Never, IncidentResponse]) -> None:
        prompt = (
            "Incident analysis from the classification agent:\n"
            f"{json.dumps(analysis.to_dict(), indent=2)}"
        )
        solution = await self._helper.ask_solution_agent(prompt)
        await ctx.yield_output(IncidentResponse(analysis=analysis, solution=solution))


class CitrixHelper:
    """One conversation about one incident at a time."""

    def __init__(self) -> None:
        config = load_config()
        self._solution_agent = FoundryAgent(
            project_endpoint=config.endpoint,
            agent_name=config.solution_agent_name,
            agent_version=config.solution_agent_version,
            credential=DefaultAzureCredential(),
        )
        self._source_urls = _load_source_urls()
        self._session: AgentSession | None = None

    async def new_incident(self, incident: Incident) -> IncidentResponse:
        """Run the full classify → solve workflow and start a fresh conversation."""
        self._session = self._solution_agent.create_session()

        classify = ClassifyExecutor()
        solve = SolveExecutor(self)
        workflow = WorkflowBuilder(start_executor=classify).add_edge(classify, solve).build()

        result = await workflow.run(incident)
        outputs = result.get_outputs()
        if not outputs:
            raise RuntimeError(f"Workflow finished without output (state: {result.get_final_state()})")
        return outputs[-1]

    async def follow_up(self, question: str) -> Solution:
        """Ask the solution agent a follow-up in the current incident's conversation."""
        if self._session is None:
            raise RuntimeError("Start with new_incident() before asking follow-ups")
        return await self.ask_solution_agent(question)

    async def ask_solution_agent(self, text: str) -> Solution:
        response = await self._solution_agent.run(text, session=self._session)
        return Solution(answer=response.text.strip(), sources=self._cited_sources(response))

    def _cited_sources(self, response: AgentResponse) -> list[str]:
        """Collect the docs File Search cited, as URLs, in first-cited order."""
        sources: list[str] = []
        for message in response.messages:
            for content in message.contents:
                for annotation in getattr(content, "annotations", None) or []:
                    name = annotation.get("url") or annotation.get("file_id")
                    if not name:
                        continue
                    source = self._source_urls.get(name, name)
                    if source not in sources:
                        sources.append(source)
        return sources
