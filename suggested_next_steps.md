# Suggested Next Steps & Enhancements for Local Ollama Agent Harness

## Executive Overview
The **Local Ollama Agent Harness** is a privacy-first, local-only coding agent platform that pairs a Next.js/Tailwind control plane with a FastAPI backend constrained to a workspace sandbox and loopback Ollama daemon.

Following an in-depth codebase audit across backend and frontend systems, this document details current capabilities and outlines strategic next steps for implementation across Phase 4 (Frontend UI & Real-Time Monitoring), security hardening, and developer experience.

---

## Key Improvement Areas & Implementation Status

### 1. Semantic Codebase Indexing & Hybrid Search (Phase 1)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Local vector embeddings using Ollama's `POST /api/embed` / `/api/embeddings` endpoint, governed by `OllamaRateLimiter`.
  * Text file chunking (character chunks with overlap) stored in SQLite (`file_embeddings` table).
  * Cosine similarity vector search exposed via `SemanticSearch` in `search_tools.py` and `POST /api/search/semantic`.

### 2. Fine-Grained Action Approvals & Granular Auditing (Phase 2)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Multi-column filtering on SQLite audit entries (`GET /api/audit` supports `actor`, `action_type`, `tool_name`, `result`, `start_date`, `end_date`, `limit`, and `query`).
  * Full CSV and JSON audit record export support via `format=csv` / `format=json`.

### 3. Session Persistence, Export & Replay (Phase 2)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Markdown and JSON session transcript export (`GET /api/sessions/{session_id}/export?format=markdown|json`).
  * Point-in-time session branching/forking from any message or tool checkpoint (`POST /api/sessions/{session_id}/fork`).

### 4. Advanced Process Sandboxing & Platform Adaptability (Phase 3)
* **Status:** Proposed / Architectural Specification
* **Proposed Enhancements:**
  * **Containerized Sandbox Adapter:** Introduce a Docker/Podman container adapter alongside Linux `unshare` for developers on macOS/Windows (via WSL2 or local docker engine) where unshare namespace creation is restricted.
  * **Fine-Grained Binary Argument Rules:** Extend `CommandAllowlist` with subcommand-level pattern validation (e.g., restricting `git checkout` to local branch switching only, disallowing paths that match ignored patterns).
  * **Resource Quotas (cgroups v2):** Integrate cgroups memory (e.g. 512MB) and CPU quotas on executed processes to prevent fork bombs or CPU starvation.

### 5. Frontend UI & Real-Time Monitoring Enhancements (Phase 4)
* **Status:** **In Progress (Active Implementation)**
* **Capabilities to Implement:**
  * **Session Export & Fork UI:** Add one-click buttons in the Chat session strip to export transcript (Markdown / JSON) and fork the active session into a new branch.
  * **Interactive Audit Filtering & CSV Download:** Equip the Audit tab with filter controls (actor, action type, text search query, result) and a direct CSV download trigger.
  * **Semantic Search & Indexing Control:** Provide a search bar in the Files/Workspace view to execute semantic queries against indexed files and trigger index refreshes.
  * **Real-Time Generation Telemetry:** Calculate and display real-time streaming tokens/sec, response latency, and token counters directly during active agent streaming.
  * **Theme & Ergonomics:** Persistent dark/light mode toggle with accessible system contrast.

---

## Strategic Roadmap

| Phase | Target Deliverable | Status | Expected Benefit |
|---|---|---|---|
| **Phase 1** | Local Ollama Semantic Indexing & Vector Search | **Completed** | High-precision codebase context retrieval for local LLMs |
| **Phase 2** | Audit Filtering & Session Export / Forking Backend | **Completed** | Complete auditability and reproducible developer workflows |
| **Phase 3** | Cross-Platform Container Sandbox (Docker/bwrap) | Proposed | Broadened platform support without sacrificing safety posture |
| **Phase 4** | Enhanced UI Telemetry, Session Export/Fork & Audit Filters | **Active** | Real-time agent execution insights, UI control over backend Phase 1 & 2 APIs |
