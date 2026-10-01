# Suggested Next Steps: Local Ollama Agent Harness

This document outlines key technical, architectural, and usability enhancements for the **Local Ollama Agent Harness**. These suggestions focus on preserving the strict local-only safety posture while improving model interoperability, retrieval capabilities, codebase visibility, and user control.

---

## 1. Local Semantic Embedding Indexing & Vector Search

### Current State
`backend/app/indexing/embeddings.py` is currently an unconfigured stub. The workspace indexer (`indexer.py`) indexes basic file metadata (path, SHA-256 hash, size, modification timestamp) into SQLite (`file_index`), while code search relies exclusively on exact string keyword matching (`keyword_search` in `search_tools.py`).

### Proposed Improvements
- **Local Ollama Vector Embeddings:** Implement `embeddings(model, prompt)` in `backend/app/ollama_client.py` calling Ollama's `POST /api/embeddings` or `POST /api/embed` endpoint.
- **SQLite Vector Store & Chunking:** In `backend/app/indexing/embeddings.py`, extract text chunks from indexed workspace files, compute vector embeddings locally, and store vector representations alongside text chunk metadata in SQLite.
- **Semantic Search Tool:** Add a `semantic_search` tool method to `backend/app/tools/search_tools.py` that computes prompt embeddings, evaluates cosine similarity against indexed workspace chunks, and returns ranked relevance results.
- **Loopback & Safety Compliance:** Ensure all embedding operations route strictly through the validated loopback `OllamaClient` and respect the shared `OllamaRateLimiter`.

---

## 2. ReAct Fallback Parsing & Small-Model Robustness

### Current State
When non-function-calling models run in ReAct mode, `backend/app/orchestrator.py` expects the model to output raw JSON objects matching `{"action": "tool_name", "arguments": {...}}` or `{"final": "..."}`. Small local models frequently wrap JSON inside markdown code fences (e.g. ` ```json ... ``` `) or include leading/trailing whitespace, leading to unnecessary JSON parse failures.

### Proposed Improvements
- **Markdown Code Fence Stripping:** Update `AgentOrchestrator._parse_react_response()` in `backend/app/orchestrator.py` to extract JSON from code blocks before attempting `json.loads`.
- **Fuzzy Output Repair:** Handle leading/trailing conversational text gracefully by extracting candidate JSON object boundaries (`{ ... }`) when raw parsing fails.
- **Enhanced Model Feedback:** Provide clear, structured error responses when JSON is invalid so the model can self-correct within budget limits.

---

## 3. Workspace Structural Summary Tooling

### Current State
When an agent starts in a new workspace, it must run multiple `list_files` calls to understand the codebase layout. On large repositories, this consumes precious turns and context budget.

### Proposed Improvements
- **`workspace_summary` Tool:** Add a pure-Python analysis tool in `backend/app/tools/fs_tools.py` that scans the workspace root, aggregates file counts by extension, calculates line counts, detects major language frameworks, and returns a high-level structural map.
- **Tool Schema Registration:** Expose `workspace_summary` in `backend/app/tools/__init__.py` with proper JSON schema parameters so models can invoke it at session start.

---

## 4. Frontend & API Search Enhancements

### Current State
The Next.js frontend (`frontend/components/HarnessDashboard.tsx`) allows file browsing and content previewing, but lacks direct search interfaces for semantic or keyword queries from the Files view.

### Proposed Improvements
- **Semantic Search Endpoint:** Expose `POST /api/index/semantic-search` in `backend/app/main.py`.
- **Files Tab Semantic Search Bar:** Update `HarnessDashboard.tsx` to include an interactive semantic search input in the Files view, displaying ranked search matches with relevance scores and file preview snippets.

---

## 5. Summary of Implementation Goals

| Area | Feature / Change | Impact |
| --- | --- | --- |
| **Indexing & Search** | Local vector embeddings (`/api/embeddings`) + `semantic_search` | Enables conceptual code discovery without cloud dependency |
| **Orchestration** | Robust ReAct markdown block parsing | Prevents JSON parse errors on small local models |
| **Tools** | `workspace_summary` structural analysis tool | Accelerates agent onboarding on new repositories |
| **UI & API** | Interactive semantic search in Files tab & `POST /api/index/semantic-search` | Provides instant code retrieval in the control plane |
