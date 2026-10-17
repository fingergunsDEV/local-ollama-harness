# Suggested Next Steps & Enhancements for Local Ollama Agent Harness

## Executive Overview
The **Local Ollama Agent Harness** is a privacy-first, local-only coding agent platform that pairs a Next.js/Tailwind control plane with a FastAPI backend constrained to a workspace sandbox and loopback Ollama daemon.

Following an exhaustive scan of the backend Python codebase (`app/`) and Next.js frontend (`frontend/`), this document outlines key areas of improvement across core capabilities, security/sandboxing, indexing/search, user interface, and operational resilience.

---

## Key Improvement Areas

### 1. Semantic Codebase Indexing & Hybrid Search (Priority 1)
* **Current State:** `backend/app/indexing/embeddings.py` is an empty stub ("Semantic indexing is intentionally optional and disabled in v1"). Search currently relies strictly on regex/keyword file scanning.
* **Proposed Enhancement:**
  * Implement local vector embeddings using Ollama's `POST /api/embed` endpoint, governed by `OllamaRateLimiter`.
  * Chunk indexed text files (256–512 token chunks with overlap) and store chunk vector embeddings in SQLite (`embeddings` table).
  * Expose vector similarity (cosine distance) search via `SemanticSearch` in `search_tools.py` and a dedicated `GET /api/search/semantic` endpoint.
  * Fall back gracefully to keyword search if no embedding model is configured/available.

### 2. Fine-Grained Action Approvals & Granular Auditing (Priority 2)
* **Current State:** Approvals are coarse-grained (approve/deny whole action category or session-remember).
* **Proposed Enhancement:**
  * Support line-level / diff-chunk level approval for multi-file edits.
  * Add rich filtering and query capabilities on the SQLite audit trail (`GET /api/audit` by session, status, tool name, or date range).
  * Enable JSON/CSV export for audit records.

### 3. Session Persistence, Export & Replay (Priority 2)
* **Current State:** Session history stores chat messages and tool executions in SQLite, but lacks export or point-in-time replay/branching.
* **Proposed Enhancement:**
  * Add Markdown and JSON session transcript export (`GET /api/sessions/{id}/export`).
  * Support session branching/forking from any message or tool output checkpoint.

### 4. Advanced Process Sandboxing & Platform Adaptability (Priority 3)
* **Current State:** `EXEC_REQUIRE_OS_SANDBOX=true` uses Linux `unshare` namespaces. On non-Linux host platforms (macOS/Windows) or unprivileged containers, command execution fails closed.
* **Proposed Enhancement:**
  * Implement an optional Docker/Podman or bubblewrap container adapter for non-Linux or containerized developer environments.
  * Enhance allowlist regex matching to detect obfuscated commands or chained arguments.

### 5. Frontend UI & Real-Time Monitoring Enhancements (Priority 3)
* **Current State:** `HarnessDashboard.tsx` provides streaming chat, diff previews, and approval modals.
* **Proposed Enhancement:**
  * Add an interactive visual representation of workspace file tree indexing status and embedding status badges.
  * Provide live latency and tokens-per-second metrics during stream generation.
  * Add dark/light mode toggle persistence and accessibility keyboard navigation shortcuts.

---

## Strategic Roadmap

| Phase | Target Deliverable | Expected Benefit | Status |
|---|---|---|---|
| **Phase 1** | Local Ollama Semantic Indexing & Vector Search | High-precision codebase context retrieval for local LLMs | Completed |
| **Phase 2** | Audit Filtering & Session Export / Forking | Complete auditability and reproducible developer workflows | In Progress |
| **Phase 3** | Cross-Platform Container Sandbox (Docker/bwrap) | Broadened platform support without sacrificing safety posture | Planned |
| **Phase 4** | Enhanced UI Telemetry & Workspace File Explorer | Real-time agent execution insights and improved UX | Planned |

---

## Detailed Implementation Notes (Phase 1 & Phase 2)

### Session Export (`GET /api/sessions/{session_id}/export`)
* **Formats Supported:** `markdown` (human-readable transcript with role headers and tool calls) and `json` (structured JSON dump of session metadata and message array).
* **Endpoints:** `GET /api/sessions/{session_id}/export?format=markdown|json`

### Audit Trail Filtering & CSV Export (`GET /api/audit`)
* **Filtering Parameters:**
  * `session_id`: Filter logs by specific session ID.
  * `actor`: Filter by actor (`user` or `agent`).
  * `action_type`: Filter by specific action (e.g., `tool_call`, `dry_run_toggle`, `approval_resolve`).
  * `result`: Filter by outcome (`success`, `denied`, `error`, `failed`).
  * `date_from` / `date_to`: ISO timestamp range limits.
* **Export Formats:** `format=json` (default JSON payload) or `format=csv` (Response with `text/csv` content type and header disposition).

### Semantic Indexing & Embedding Tests
* Full unit test coverage added in `backend/tests/test_indexing.py` testing `chunk_text`, `cosine_similarity`, `LocalEmbeddingProvider` fallback to `/api/embeddings`, `LocalIndexer.generate_embeddings_for_file`, and `SearchTools.semantic_search`.
