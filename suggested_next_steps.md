# Suggested Next Steps & Enhancements for Local Ollama Agent Harness

## Executive Overview
The **Local Ollama Agent Harness** is a privacy-first, local-only coding agent platform that pairs a Next.js/Tailwind control plane with a FastAPI backend constrained to a workspace sandbox and loopback Ollama daemon.

Following an exhaustive scan of the backend Python codebase (`app/`) and Next.js frontend (`frontend/`), this document outlines key areas of improvement across core capabilities, security/sandboxing, indexing/search, user interface, and operational resilience, including recently implemented enhancements.

---

## Recently Implemented Improvements

### 1. Local Ollama Vector Embeddings & Semantic Search (Completed)
* **Implemented Solution:**
  * Local vector embeddings powered by Ollama's `POST /api/embed` endpoint in `backend/app/indexing/embeddings.py`.
  * Chunking text files with overlapping character bounds and storing chunk vectors in SQLite `file_embeddings`.
  * Exposing semantic vector similarity search via `GET /api/search/semantic` and frontend Search UI tab.

### 2. Session Persistence, Transcript Export & Branching/Forking (Completed)
* **Implemented Solution:**
  * Endpoint `GET /api/sessions/{id}/export?format=json|markdown` providing full transcript exports in JSON and Markdown.
  * Endpoint `POST /api/sessions/{id}/fork` allowing sessions to be branched/forked from any message checkpoint.
  * Interactive UI controls in `HarnessDashboard.tsx` for one-click session export and forking.

### 3. Granular Audit Log Filtering & CSV Export (Completed)
* **Implemented Solution:**
  * Multi-param filtering (`actor`, `action_type`, `result`, `query`) on `GET /api/audit`.
  * CSV export formatted stream via `GET /api/audit?format=csv`.
  * Interactive UI filter bar and CSV export button on the Audit tab.

---

## Future Strategic Roadmap & Further Enhancements

### 1. Line-Level Action Approvals & Granular Diffs (Priority 1)
* **Proposed Enhancement:**
  * Support line-level / diff-chunk level approval for multi-file edits rather than all-or-nothing file mutation approvals.
  * Provide interactive side-by-side diff hunk inspection in the Approval modal.

### 2. Advanced Process Sandboxing & Platform Adaptability (Priority 2)
* **Proposed Enhancement:**
  * Implement an optional Docker/Podman or bubblewrap container adapter for non-Linux host platforms (macOS/Windows) or unprivileged environments.
  * Enhance allowlist regex matching to detect obfuscated commands or chained arguments.

### 3. Real-Time Telemetry & Token Metrics (Priority 3)
* **Proposed Enhancement:**
  * Display live streaming performance metrics (tokens/sec, time-to-first-token latency) during agent execution.
  * Provide visual status indicators for indexed files and embedding freshness in the File Browser.

---

## Strategic Roadmap Summary

| Phase | Target Deliverable | Status |
|---|---|---|
| **Phase 1** | Local Ollama Semantic Indexing & Vector Search | **Completed** |
| **Phase 2** | Audit Filtering, Session Export & Forking | **Completed** |
| **Phase 3** | Line-Level Action Approvals & Diff Hunks | Planned |
| **Phase 4** | Cross-Platform Container Sandbox (Docker/bwrap) | Planned |
| **Phase 5** | Live Execution Telemetry & UI Performance Metrics | Planned |
