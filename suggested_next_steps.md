# Suggested Next Steps & Enhancements for Local Ollama Agent Harness

## Executive Overview
The **Local Ollama Agent Harness** is a privacy-first, local-only coding agent platform that pairs a Next.js/Tailwind control plane with a FastAPI backend constrained to a workspace sandbox and loopback Ollama daemon.

Following an exhaustive scan of the backend Python codebase (`backend/app/`) and Next.js frontend (`frontend/`), this document outlines key areas of improvement across core capabilities, security/sandboxing, indexing/search, user interface, and operational resilience.

---

## Key Improvement Areas

### 1. Semantic Codebase Indexing & Hybrid Search (Priority 1)
* **Current State:** Basic vector chunking and embeddings provider (`LocalEmbeddingProvider`) have been added to `backend/app/indexing/embeddings.py` and `indexer.py`, allowing vector indexing and semantic search via `GET /api/search/semantic`.
* **Proposed Enhancement:**
  * Integrate automatic background indexing refresh and embeddings generation on file change detection.
  * Enable hybrid search combining BM25/keyword scores with vector cosine similarity for enhanced retrieval precision.
  * Expose indexing progress, token count, and vector status badges directly in the control plane UI.

### 2. Fine-Grained Action Approvals & Granular Auditing (Priority 2)
* **Current State:** `GET /api/audit` supports basic target/action search, but lacks structured multi-field filtering and data export.
* **Proposed Enhancement:**
  * Support line-level / diff-chunk level approval for multi-file edits.
  * Add rich filtering capabilities on the SQLite audit trail (`GET /api/audit` by `action_type`, `result`, date ranges, and actor).
  * Enable JSON and CSV export endpoints (`GET /api/audit/export`) for compliance and external auditing.

### 3. Session Persistence, Export & Replay / Forking (Priority 2)
* **Current State:** Session history stores chat messages and tool executions in SQLite, but lacks transcript export or branching.
* **Proposed Enhancement:**
  * Add Markdown and JSON session transcript export (`GET /api/sessions/{session_id}/export`).
  * Support session branching/forking (`POST /api/sessions/{session_id}/fork`) to clone a session's state and transcript up to a given checkpoint.

### 4. Advanced Process Sandboxing & Platform Adaptability (Priority 3)
* **Current State:** `EXEC_REQUIRE_OS_SANDBOX=true` uses Linux `unshare` namespaces. On non-Linux host platforms (macOS/Windows) or unprivileged containers, command execution fails closed.
* **Proposed Enhancement:**
  * Implement an optional Docker/Podman or bubblewrap container adapter for non-Linux or containerized developer environments.
  * Enhance allowlist regex matching to detect obfuscated commands or chained arguments.

### 5. Frontend UI & Real-Time Monitoring Enhancements (Priority 3)
* **Current State:** `HarnessDashboard.tsx` provides streaming chat, diff previews, and approval modals.
* **Proposed Enhancement:**
  * Add Export Session (Markdown/JSON) and Fork Session controls directly in the chat panel.
  * Provide audit filtering controls and CSV/JSON export buttons in the audit view.
  * Show live latency and tokens-per-second metrics during stream generation.

---

## Strategic Roadmap

| Phase | Target Deliverable | Expected Benefit |
|---|---|---|
| **Phase 1** | Local Ollama Semantic Indexing & Hybrid Search | High-precision codebase context retrieval for local LLMs |
| **Phase 2** | Audit Filtering/Export & Session Export/Forking | Complete auditability and reproducible developer workflows |
| **Phase 3** | Cross-Platform Container Sandbox (Docker/bwrap) | Broadened platform support without sacrificing safety posture |
| **Phase 4** | Enhanced UI Telemetry & Workspace File Explorer | Real-time agent execution insights and improved UX |
