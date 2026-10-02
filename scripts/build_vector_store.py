"""
build_vector_store.py
=====================
Uploads every Markdown file under docs/citrix/ into a Foundry vector store
named "citrix-docs". Foundry handles chunking, embedding and indexing; the
solution agent searches it through its File Search tool.

Re-runnable: if the store already exists, its old files are removed and the
current docs are uploaded into the SAME store, so its ID never changes and
the solution agent doesn't need a new version when the docs change.

Run from the project root (after scripts/fetch_citrix_docs.py):
    python scripts/build_vector_store.py
"""

from __future__ import annotations

import sys
from contextlib import ExitStack
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import VECTOR_STORE_NAME, load_config  # noqa: E402

DOCS_DIR = PROJECT_ROOT / "docs" / "citrix"


def find_vector_store(client, name: str):
    for store in client.vector_stores.list():
        if store.name == name:
            return store
    return None


def main() -> None:
    doc_paths = sorted(DOCS_DIR.rglob("*.md"))
    if not doc_paths:
        raise SystemExit(f"No docs in {DOCS_DIR}. Run scripts/fetch_citrix_docs.py first.")

    config = load_config()
    project_client = AIProjectClient(endpoint=config.endpoint, credential=DefaultAzureCredential())
    client = project_client.get_openai_client()

    store = find_vector_store(client, VECTOR_STORE_NAME)
    if store is None:
        store = client.vector_stores.create(name=VECTOR_STORE_NAME)
        print(f"Created vector store '{VECTOR_STORE_NAME}' ({store.id})")
    else:
        old_files = list(client.vector_stores.files.list(vector_store_id=store.id))
        print(f"Reusing vector store '{VECTOR_STORE_NAME}' ({store.id}); removing {len(old_files)} old file(s)")
        for old in old_files:
            client.vector_stores.files.delete(vector_store_id=store.id, file_id=old.id)
            client.files.delete(old.id)

    print(f"Uploading {len(doc_paths)} file(s) and waiting for indexing...")
    with ExitStack() as stack:
        files = [stack.enter_context(path.open("rb")) for path in doc_paths]
        batch = client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=store.id, files=files
        )

    counts = batch.file_counts
    print(f"Done: {counts.completed} completed, {counts.failed} failed, {counts.in_progress} in progress")
    if counts.failed:
        raise SystemExit("Some files failed to index — check the vector store in the Foundry portal.")


if __name__ == "__main__":
    main()
