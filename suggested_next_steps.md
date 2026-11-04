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
  * Interactive UI filter bar (actor, action type, query) and CSV export download button in the Audit tab.

### 3. Session Persistence, Export & Replay (Implemented)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Markdown and JSON session transcript export (`GET /api/sessions/{session_id}/export?format=markdown|json`).
  * Point-in-time session branching/forking from any message or tool checkpoint (`POST /api/sessions/{session_id}/fork`).
  * User-facing export and fork buttons directly in the Chat interface session strip.

### 4. Advanced Command Obfuscation Detection & Safety Hardening (Implemented)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Enhanced `CommandAllowlist` with detection for hex/octal escape sequences (`\x`, `\0`, `\u`), URL percent-encoding (`%2e%2e`), and forbidden flag injection patterns.
  * Comprehensive validation ensuring arguments cannot bypass path resolution via encoding or escaping.

### 5. Frontend UI & Real-Time Monitoring Enhancements (Implemented)
* **Status:** **Completed**
* **Capabilities Implemented:**
  * Real-time streaming telemetry in the chat interface: live token count, duration timer, and tokens/sec calculation during Ollama generation.
  * Session management UI: Quick actions to export transcripts (Markdown / JSON) and fork existing sessions.
  * Audit log filtering UI: Multi-field filters for actor, action type, and search query with one-click CSV export.

---

## Strategic Roadmap

| Phase | Target Deliverable | Status | Expected Benefit |
|---|---|---|---|
| **Phase 1** | Local Ollama Semantic Indexing & Vector Search | **Completed** | High-precision codebase context retrieval for local LLMs |
| **Phase 2** | Audit Filtering & Session Export / Forking | **Completed** | Complete auditability and reproducible developer workflows |
| **Phase 3** | Obfuscation Detection & Enhanced Allowlist Hardening | **Completed** | Prevents argument smuggling, encoded traversals, and shell evasion |
| **Phase 4** | Real-Time UI Telemetry & Interactive Controls | **Completed** | Real-time token velocity metrics, session export, and audit filtering in UI |
| **Phase 5** | Container Sandbox Adapters (Docker/OCI) | Proposed | Alternative containerized isolation modes for non-Linux host platforms |
