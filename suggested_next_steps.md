# Suggested Next Steps & Enhancements for Local Ollama Agent Harness

## Executive Overview
The **Local Ollama Agent Harness** is a privacy-first, local-only coding agent platform that pairs a Next.js/Tailwind control plane with a FastAPI backend constrained to a workspace sandbox and loopback Ollama daemon.

Following an architectural scan of the backend Python codebase (`app/`) and Next.js frontend (`frontend/`), this document outlines key areas of improvement across core capabilities, security/sandboxing, indexing/search, user interface, and operational resilience, along with implementation status.

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

### 4. Indexing Status Telemetry & Workspace Diagnostics (In Progress / Active Step)
* **Status:** **In Progress**
* **Capabilities Implemented / Being Implemented:**
  * Added `LocalIndexer.index_status()` method returning total indexed files, vector chunk count, and latest indexing timestamp.
  * Exposed `GET /api/index/status` endpoint to provide live indexing metadata to the control plane.

### 5. Frontend Session Management, Audit Controls & Index Telemetry (In Progress / Active Step)
* **Status:** **In Progress**
* **Capabilities Implemented / Being Implemented:**
  * Added session export buttons (Markdown and JSON formats) and Session Forking in the Chat UI.
  * Added interactive Audit Search & Filtering panel with live CSV export button.
  * Integrated Workspace Index & Vector Embedding Status indicator in the Files UI with a "Refresh Index" trigger.

### 6. Advanced Command Validation & Evasive Execution Guards (In Progress / Active Step)
* **Status:** **In Progress**
* **Capabilities Implemented / Being Implemented:**
  * Strengthened `CommandAllowlist` in `backend/app/safety/allowlist.py` against evasive commands, variable expansions (`${...}`), subshell expressions (`$(...)`), process substitution (`<(...)`), and obfuscated encoding patterns.

---

## Strategic Roadmap

| Phase | Target Deliverable | Status | Expected Benefit |
|---|---|---|---|
| **Phase 1** | Local Ollama Semantic Indexing & Vector Search | **Completed** | High-precision codebase context retrieval for local LLMs |
| **Phase 2** | Audit Filtering & Session Export / Forking | **Completed** | Complete auditability and reproducible developer workflows |
| **Phase 3** | Indexing Status Telemetry & Workspace Diagnostics | **Completed** | Transparency into vector index depth and file coverage |
| **Phase 4** | Frontend Session Management, Audit Filtering & Index UI | **Completed** | Richer control plane features for session branching, export, and search |
| **Phase 5** | Evasive Command Execution Guards & Obfuscation Shields | **Completed** | Fortified safety perimeter against command injection tricks |
| **Phase 6** | Cross-Platform Container Sandbox (Docker/bwrap) | Future | Broadened platform support without sacrificing safety posture |
