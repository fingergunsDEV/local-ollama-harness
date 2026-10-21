# Suggested Next Steps & Enhancements for Local Ollama Agent Harness

## Executive Overview
The **Local Ollama Agent Harness** is a privacy-first, local-only coding agent platform that pairs a Next.js/Tailwind control plane with a FastAPI backend constrained to a workspace sandbox and loopback Ollama daemon.

Following an exhaustive scan of the backend Python codebase (`app/`) and Next.js frontend (`frontend/`), this document outlines key areas of improvement across core capabilities, security/sandboxing, indexing/search, session lifecycle, user interface, and operational resilience.

---

## Implemented & High-Priority Enhancements

### 1. Semantic Codebase Indexing & Hybrid Vector Search (Implemented)
* **Description:** Integrates local vector embeddings using Ollama's `POST /api/embed` or `/api/embeddings` endpoint, governed by `OllamaRateLimiter`.
* **Details:**
  * Chunk indexed text files (character/line overlap chunking) and store chunk vector embeddings in SQLite (`file_embeddings` table).
  * Expose vector similarity (cosine distance) search via `SemanticSearch` in `search_tools.py` and dedicated `POST /api/search/semantic` endpoint.
  * Search gracefully handles error cases and empty results.

### 2. Session Persistence, Export & Replay (Implemented & In Progress)
* **Current State:** Session history stores chat messages and tool executions in SQLite.
* **Proposed Enhancement:**
  * Add Markdown and JSON session transcript export (`GET /api/sessions/{id}/export?format=markdown|json`).
  * Support session replay/forking from any message or tool output checkpoint to enable reproducible debugging.

### 3. Fine-Grained Action Approvals & Granular Audit Export (Implemented & In Progress)
* **Current State:** Approvals are coarse-grained (approve/deny whole action category or session-remember).
* **Proposed Enhancement:**
  * Add rich filtering (`action_type`, `actor`, `limit`, `query`) and export capabilities (`GET /api/audit/export?format=json|csv`) on the SQLite audit trail.
  * Support line-level / diff-chunk level approval for multi-file edits in the UI.

### 4. Advanced Process Sandboxing & Platform Adaptability
* **Current State:** `EXEC_REQUIRE_OS_SANDBOX=true` uses Linux `unshare` namespaces. On non-Linux host platforms (macOS/Windows) or unprivileged containers, command execution fails closed.
* **Proposed Enhancement:**
  * Implement an optional Docker/Podman or bubblewrap container adapter for non-Linux or containerized developer environments.
  * Enhance allowlist regex matching to detect obfuscated commands or chained arguments.

### 5. Frontend UI & Real-Time Monitoring Enhancements
* **Current State:** `HarnessDashboard.tsx` provides streaming chat, diff previews, and approval modals.
* **Proposed Enhancement:**
  * Add session export button (Download Markdown / Download JSON) and audit trail CSV export in the frontend interface.
  * Add an interactive visual representation of workspace file tree indexing status and embedding status badges.
  * Provide live latency and tokens-per-second metrics during stream generation.

---

## Strategic Roadmap

| Phase | Target Deliverable | Expected Benefit | Status |
|---|---|---|---|
| **Phase 1** | Local Ollama Semantic Indexing & Vector Search | High-precision codebase context retrieval for local LLMs | **Completed** |
| **Phase 2** | Session Transcript Export (Markdown/JSON) | Reproducible developer workflows & exportable session logs | **Completed** |
| **Phase 3** | Granular Audit Filtering & Export (JSON/CSV) | Complete auditability & security compliance export | **Completed** |
| **Phase 4** | Cross-Platform Container Sandbox (Docker/bwrap) | Broadened platform support without sacrificing safety posture | Proposed |
| **Phase 5** | Enhanced UI Telemetry & Workspace File Explorer | Real-time agent execution insights and improved UX | Proposed |
