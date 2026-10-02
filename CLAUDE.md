Project goals
1. Create a working prototype that demonstrates multi agents orchestration. The overall goal is to create a simple Citrix helper app.
2. One agent will classify Citrix problem
3. Another agent will look for the solution via RAG

Architecture
- `main.py` — terminal chat. New incident → full workflow; follow-ups go only to the solution agent (same session). `--json` also prints the classification JSON.
- `orchestrator.py` — Microsoft Agent Framework workflow: `ClassifyExecutor` (wraps `analyzer.analyze_incident`) → `SolveExecutor` (solution agent). `CitrixHelper` owns the solution agent session and maps File Search citations back to doc URLs.
- `analyzer.py` / `ai_classification.py` / `extraction.py` — classification step. Classifier Foundry agent returns category + confidence; priority, error codes and user count come from regex in `extraction.py`. `classification.py` is the old keyword classifier (unused).
- `models.py` — shared dataclasses: `Incident`, `AnalysisResult` (+ `to_dict()`), `Solution`, `IncidentResponse`.
- `config.py` — Foundry endpoint, agent names/versions read from `.env` (git-ignored; template in `.env.example`), `VECTOR_STORE_NAME`. Never hardcode endpoints, agent names or keys in code — this repo is public.

Foundry resources
- Classifier agent: name set by `AZURE_AI_AGENT_NAME` (created in the portal).
- Solution agent: `citrix-solution-agent` — prompt agent with File Search over the `citrix-docs` vector store. Created by `scripts/create_solution_agent.py`; its instructions live in that script. Each run creates a new version → update `AZURE_AI_SOLUTION_AGENT_VERSION` in `.env`.
- Vector store `citrix-docs` — built by `scripts/build_vector_store.py` from `docs/citrix/**/*.md`. Re-running replaces the files but keeps the same store ID, so no new agent version is needed.

Updating the docs
1. Edit `docs/sources.txt` (`<category> | <url>`).
2. `python scripts/fetch_citrix_docs.py` (regenerates `docs/citrix/`; each file starts with `Source: <url>`).
3. `python scripts/build_vector_store.py`.

LLM model
- The model is configured on the Azure AI Foundry agent (name/version in config.py), not in code. It changes without code changes.
- Don't assume a model from comments or docstrings. Check the `model:` line ai_classification.py prints to stderr (from `response.model`), or ask.
