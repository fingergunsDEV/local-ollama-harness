# Suggested Next Steps and Architecture Improvements

This document outlines recommended improvements and strategic roadmap items for the **Local Ollama Agent Harness**.

---

## 1. Local Vector & Semantic Code Search Integration

### Current State
File search currently relies on literal string searching and regex matching (`backend/app/tools/search_tools.py`), and metadata indexing (`backend/app/indexing/indexer.py`). `backend/app/indexing/embeddings.py` is stubbed out for v1.

### Proposed Improvement
- Implement `OllamaEmbeddings` in `backend/app/indexing/embeddings.py` using Ollama's local `/api/embed` endpoint.
- Integrate vector storage in SQLite (`sqlite-vss` or vector similarity via cosine distance in Python/SQLite).
- Store chunked file embeddings during `LocalIndexer.refresh()`.
- Add a `semantic_search` tool to `ToolRegistry` so the LLM agent can find code snippets by semantic meaning without relying purely on exact keyword or symbol matches.

---

## 2. Audit Trail Analytics & Export Endpoints

### Current State
Audit logs are written to an append-only JSONL file and mirrored into SQLite (`backend/app/audit/logger.py`). The API provides basic retrieval (`GET /api/audit`), but lacks filtering and export formats.

### Proposed Improvement
- Add `GET /api/audit/export` supporting `format=json` and `format=csv`.
- Enable filtering by date range, action type, actor, and result status in `SessionStore.audit_entries()`.
- Add audit summary statistics (e.g. counts of approved vs. denied actions, rate limit events) to help operators monitor agent compliance.

---

## 3. Webhook / Desktop Notifications for Pending Approvals

### Current State
Approvals pause execution and poll/wait via SSE stream and frontend `ApprovalModal`. If an operator switches tabs or leaves the UI, pending approvals might time out after `max_wall_clock_seconds`.

### Proposed Improvement
- Add Web Notification API support in the Next.js frontend (`frontend/components/ApprovalModal.tsx`).
- Support optional webhooks or local OS desktop notifications when high-risk actions require user intervention.

---

## 4. Enhanced Workspace Snapshot & Visual Diff Revert Tooling

### Current State
`write_file` and `delete_file` create pre-change snapshots stored in `.harness-snapshots`. A restore endpoint `POST /api/snapshots/restore` exists.

### Proposed Improvement
- Provide a dedicated UI tab or side-by-side modal for viewing `.harness-snapshots` diffs.
- Support multi-file snapshot rollback/revert checkpoints for multi-step agent refactoring tasks.

---

## 5. Security Sandbox Monitoring & Fallback Diagnostics

### Current State
`sandbox.py` enforces namespace isolation using `unshare` on Linux systems. If `unshare` is not available, execution fails closed.

### Proposed Improvement
- Provide clearer diagnostic output in `GET /api/health` or `GET /api/settings` detailing sandbox availability (e.g., Linux unshare capability check, mount permissions).
- Include structured error reporting in the UI when execution is blocked due to sandbox constraints.

---

## 6. Automated Evaluation & Benchmark Suite

### Current State
Pytest unit tests cover safety gates, rate limiting, and sandbox traversal checks.

### Proposed Improvement
- Build an offline replay/benchmark suite that runs standard coding agent tasks against saved mock Ollama responses.
- Track success rates, step count efficiency, and adherence to safety guidelines across different model sizes (e.g. Llama 3.1 8B vs. Qwen 2.5 14B).
