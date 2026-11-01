# Suggested Next Steps & Enhancements for Local Ollama Agent Harness

## Executive Overview
The **Local Ollama Agent Harness** is a privacy-first, local-only coding agent platform that pairs a Next.js/Tailwind control plane with a FastAPI backend constrained to a workspace sandbox and loopback Ollama daemon.

Following an exhaustive scan of the backend Python codebase (`app/`) and Next.js frontend (`frontend/`), this document outlines key areas of improvement across core capabilities, security/sandboxing, indexing/search, user interface, and operational resilience, along with implementation status.

---

## Key Improvement Areas & Implementation Status

### 1. Semantic Codebase Indexing & Hybrid Search (Implemented)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Local vector embeddings using Ollama's `POST /api/embed` / `/api/embeddings` endpoint, governed by `OllamaRateLimiter`.
  * Text file chunking (character chunks with overlap) stored in SQLite (`file_embeddings` table).
  * Cosine similarity vector search exposed via `SemanticSearch` in `search_tools.py` and `POST /api/search/semantic`.

### 2. Fine-Grained Action Approvals & Granular Auditing (Implemented)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Multi-column filtering on SQLite audit entries (`GET /api/audit` supports `actor`, `action_type`, `tool_name`, `result`, `start_date`, `end_date`, `limit`, and `query`).
  * Full CSV and JSON audit record export support via `format=csv` / `format=json`.

### 3. Session Persistence, Export & Replay (Implemented)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Markdown and JSON session transcript export (`GET /api/sessions/{session_id}/export?format=markdown|json`).
  * Point-in-time session branching/forking from any message or tool checkpoint (`POST /api/sessions/{session_id}/fork`).

### 4. Surgical File Patching & Targeted Code Edits (Implemented)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Targeted search-and-replace edits via `patch_file` (`FileTools.patch_file`) preventing full file overwrites.
  * Strict validation guaranteeing the search block is unique in the target file.
  * Dry-run unified diff generation and integration with approval gating under the `"write"` action type.

### 5. Snapshot Discovery & Inspection API (Implemented)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Added `ToolRegistry.list_snapshots` and `GET /api/snapshots` to list available `.harness-snapshots` backups with metadata (id, size, created_at).
  * Allows operators to inspect active pre-change snapshots prior to executing rollback via `POST /api/snapshots/restore`.

### 6. Advanced Process Sandboxing & Platform Adaptability (Future Phase)
* **Status:** Proposed
* **Proposed Enhancement:**
  * Implement an optional Docker/Podman or bubblewrap container adapter for non-Linux or containerized developer environments.
  * Enhance allowlist regex matching to detect obfuscated commands or chained arguments.

### 7. Frontend UI & Real-Time Monitoring Enhancements (Future Phase)
* **Status:** Proposed
* **Proposed Enhancement:**
  * Add an interactive visual representation of workspace file tree indexing status and embedding status badges in the UI.
  * Provide live latency and tokens-per-second metrics during stream generation.
  * Add dark/light mode toggle persistence and accessibility keyboard navigation shortcuts.

---

## Strategic Roadmap

| Phase | Target Deliverable | Status | Expected Benefit |
|---|---|---|---|
| **Phase 1** | Local Ollama Semantic Indexing & Vector Search | **Completed** | High-precision codebase context retrieval for local LLMs |
| **Phase 2** | Audit Filtering & Session Export / Forking | **Completed** | Complete auditability and reproducible developer workflows |
| **Phase 3** | Surgical File Patching & Snapshot Management API | **Completed** | Efficient targeted edits and snapshot inspection for operators |
| **Phase 4** | Cross-Platform Container Sandbox (Docker/bwrap) | Proposed | Broadened platform support without sacrificing safety posture |
| **Phase 5** | Enhanced UI Telemetry & Workspace File Explorer | Proposed | Real-time agent execution insights and improved UX |
