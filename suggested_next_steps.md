# Suggested Next Steps & Enhancements for Local Ollama Agent Harness

## Executive Overview
The **Local Ollama Agent Harness** is a privacy-first, local-only coding agent platform that pairs a Next.js/Tailwind control plane with a FastAPI backend constrained to a workspace sandbox and loopback Ollama daemon.

Following an exhaustive scan of the backend Python codebase (`backend/app/`) and Next.js frontend (`frontend/`), this document outlines key areas of improvement across core capabilities, security/sandboxing, indexing/search, user interface, and operational resilience.

---

## Codebase Scan Findings & Implementation Status

### Current Architecture Strengths
1. **Strict Loopback & Sandbox Controls:** Restricted workspace path canonicalization, `.env` and `.git/config` blocking, and non-loopback Ollama connection rejection.
2. **OS Process Sandboxing:** Command execution requires Linux `unshare` namespaces (user, mount, network, PID), failing closed when unavailable.
3. **Approval-Gated Workflows:** Dry-run modes for file mutations and commands, approval queues, and pre-change `.harness-snapshots` backups.
4. **Local Indexing Infrastructure:** Local SQLite metadata tracking and `LocalEmbeddingProvider` / `LocalIndexer` infrastructure using Ollama `/api/embed` and `/api/embeddings`.

---

## Key Improvement Areas & Next Steps

### 1. Semantic Codebase Indexing & Hybrid Search Integration (Priority 1)
* **Current State:** `LocalEmbeddingProvider` and `LocalIndexer` are implemented in `backend/app/indexing/`, but `semantic_search` was not registered as a tool schema accessible to the LLM agent.
* **Actionable Next Steps:**
  * Register `semantic_search` in `TOOL_SCHEMAS` and handler dispatch in `ToolRegistry` (`backend/app/tools/__init__.py`).
  * Support automatic background chunking and embedding generation for newly created or updated files.
  * Integrate hybrid ranking (combining keyword/exact match with semantic cosine similarity scores).

### 2. Session Transcript Export & Replay Support (Priority 1)
* **Current State:** Sessions and message histories are persisted in SQLite (`backend/app/db/session_store.py`), but lacked direct export options in standard formats.
* **Actionable Next Steps:**
  * Add a session export endpoint (`GET /api/sessions/{session_id}/export?format=json|md`) returning full transcript, tool calls, and execution metadata in JSON or Markdown.
  * Implement session branching/forking capabilities allowing operators to resume/branch from an earlier checkpoint message.

### 3. Granular Audit Log Export & Advanced Filtering (Priority 2)
* **Current State:** Audit logs are saved in SQLite and JSONL, but API responses only provided basic session/query filter parameters without export capabilities.
* **Actionable Next Steps:**
  * Expose an audit log export endpoint (`GET /api/audit/export?format=json|csv`) allowing export of compliance and execution records.
  * Add date-range, tool-name, and actor filters to the `/api/audit` endpoint.

### 4. Cross-Platform Container Sandboxing (Priority 3)
* **Current State:** `EXEC_REQUIRE_OS_SANDBOX=true` uses Linux `unshare` namespaces. Execution fails closed on macOS/Windows host environments.
* **Actionable Next Steps:**
  * Add an optional Docker/Podman container adapter fallback for non-Linux or containerized local dev environments.
  * Improve command allowlist pattern matching for nested or multi-argument execution.

### 5. Frontend Visual Telemetry & Workspace Explorer Enhancements (Priority 3)
* **Current State:** Next.js dashboard provides streaming SSE response view, diff previews, and approval dialogs.
* **Actionable Next Steps:**
  * Display live vector embedding status badges and file indexing stats in the Workspace Files view.
  * Show streaming generation telemetry (tokens/sec, latency, wall-clock duration) in the chat panel.
  * Add keyboard navigation shortcuts and dark/light theme persistence.

---

## Strategic Implementation Roadmap

| Phase | Target Feature | Deliverables |
|---|---|---|
| **Phase 1** | Agent Semantic Search & Transcript Export | Register `semantic_search` tool; implement `GET /api/sessions/{id}/export` (JSON/MD) & `GET /api/audit/export` (JSON/CSV) |
| **Phase 2** | Session Forking & Advanced Audit Filtering | Add session branching from message ID; date-range & tool filters on audit API |
| **Phase 3** | Docker/Podman Container Adapter | Cross-platform sandbox support for macOS/Windows |
| **Phase 4** | UI Telemetry & Indexing Badges | Live tokens/sec display, indexing status indicators, keyboard shortcuts |
