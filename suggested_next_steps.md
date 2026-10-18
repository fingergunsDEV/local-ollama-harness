# Suggested Next Steps & Enhancements for Local Ollama Agent Harness

## Executive Overview
The **Local Ollama Agent Harness** is a privacy-first, local-only coding agent platform that pairs a Next.js/Tailwind control plane with a FastAPI backend constrained to a workspace sandbox and loopback Ollama daemon.

Following an exhaustive scan of the backend Python codebase (`app/`) and Next.js frontend (`frontend/`), this document outlines key areas of improvement across core capabilities, security/sandboxing, indexing/search, user interface, and operational resilience.

---

## Key Improvement Areas & Implementation Status

### 1. Semantic Codebase Indexing & Hybrid Search (Priority 1) — **[IMPLEMENTED]**
* **Status:** Implemented local vector embeddings using Ollama's `POST /api/embed` / `/api/embeddings` endpoint, governed by `OllamaRateLimiter`.
* **Key Features:**
  * Text chunking (500 char chunks with 50 char overlap) and SQLite vector storage (`file_embeddings` table).
  * Cosine similarity vector search via `SearchTools.semantic_search` and `POST /api/search/semantic`.
  * Manual & automated file embedding generation endpoint (`POST /api/index/embed-file`).

### 2. Fine-Grained Action Approvals & Granular Auditing (Priority 2) — **[IN PROGRESS]**
* **Status:** Enhanced audit querying and export capabilities.
* **Key Features:**
  * Rich filtering on SQLite audit trail (`GET /api/audit` by session, action_type, actor, result, or query).
  * JSON and CSV download export formats (`GET /api/audit/export`).
  * Future: Line-level / diff-chunk level approval UI for multi-file edits.

### 3. Session Persistence, Export & Forking / Replay (Priority 2) — **[IN PROGRESS]**
* **Status:** Session export and checkpoint branching implemented.
* **Key Features:**
  * Markdown (`?format=markdown`) and JSON (`?format=json`) session transcript export (`GET /api/sessions/{id}/export`).
  * Session branching/forking from any message checkpoint (`POST /api/sessions/{id}/fork`).

### 4. Advanced Process Sandboxing & Platform Adaptability (Priority 3)
* **Current State:** `EXEC_REQUIRE_OS_SANDBOX=true` uses Linux `unshare` namespaces. On non-Linux host platforms (macOS/Windows) or unprivileged containers, command execution fails closed.
* **Proposed Enhancement:**
  * Implement an optional Docker/Podman or bubblewrap container adapter for non-Linux or containerized developer environments.
  * Enhance allowlist regex matching to detect obfuscated commands or chained arguments.

### 5. Frontend UI & Real-Time Monitoring Enhancements (Priority 3)
* **Current State:** `HarnessDashboard.tsx` provides streaming chat, diff previews, and approval modals.
* **Proposed Enhancement:**
  * Add interactive export buttons for sessions and audit logs in the control plane.
  * Provide live latency and tokens-per-second metrics during stream generation.
  * Add dark/light mode toggle persistence and accessibility keyboard navigation shortcuts.

---

## Strategic Roadmap

| Phase | Target Deliverable | Status |
|---|---|---|
| **Phase 1** | Local Ollama Semantic Indexing & Vector Search | Implemented |
| **Phase 2** | Audit Filtering & Session Export / Forking | Implemented |
| **Phase 3** | Cross-Platform Container Sandbox (Docker/bwrap) | Next Priority |
| **Phase 4** | Enhanced UI Telemetry & Workspace File Explorer | Next Priority |
