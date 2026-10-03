# Suggested Next Steps & Architectural Improvements

This document outlines recommended improvements, architectural refinements, and future roadmap items for the **Local Ollama Agent Harness**.

---

## 1. Core Architecture & System Resilience

### 1.1 Local Embeddings & Semantic Search
- **Current State:** `backend/app/indexing/embeddings.py` is currently a placeholder module stating semantic indexing is disabled in v1. `LocalIndexer` only supports basic string metadata indexing.
- **Recommendation:** Implement semantic vector indexing using Ollama's local `POST /api/embed` endpoint.
- **Key Requirements:**
  - Standardize on a compact local embedding model (e.g., `nomic-embed-text` or `all-minilm`).
  - Store vector embeddings locally in SQLite via `sqlite-vec` or direct BLOB cosine calculations for low-dependency setups.
  - Enforce the same loopback-only IP check and `OllamaRateLimiter` backpressure on embedding calls.

### 1.2 Session State & Context Recovery
- **Current State:** Truncation is character-based (`48,000` chars max) in `_fit_context`. Long-running tasks risk dropping critical early tool results or context.
- **Recommendation:** Implement dynamic token budgeting and automatic context summarization.
  - Query model capabilities via `POST /api/show` to extract actual `num_ctx` limits.
  - When context usage exceeds 80% of `num_ctx`, invoke a lightweight summarization pass to collapse older tool outputs while preserving initial system constraints and user objectives.

---

## 2. Security & Governance Enhancements

### 2.1 Granular Action Risk Tiers & Multi-Level Approvals
- **Current State:** Approval categories are binary (in `approval_actions` list or auto-approved).
- **Recommendation:** Transition to a 3-tier risk system (Low / Medium / High):
  - **Low (Auto-run):** `read_file`, `list_files`, `keyword_search`, `stat_file`.
  - **Medium (Configurable session auto-approve):** `create_file`, `write_file`, non-destructive `git` operations.
  - **High (Always require explicit user confirmation):** `delete_file`, `exec` commands, `git checkout`, file restores.

### 2.2 Pre-Execution Dry-Run Diff Preview Enhancements
- **Current State:** Unified diffs are shown in tool cards, but structured diffs for binary files or large file deletions could be clearer.
- **Recommendation:** Add side-by-side syntax-highlighted diff rendering in the Next.js control plane and expand file deletion safety checks to confirm file content before unlinking.

---

## 3. Operations & Observability

### 3.1 Snapshot Lifecycle Management
- **Current State:** Overwrite and delete operations generate `.bak` files in `.harness-snapshots/`, but there was no API to list available snapshots or manage snapshot retention.
- **Recommendation:**
  - Add `GET /api/snapshots` to return formatted metadata (session ID, target file, timestamp, file size).
  - Expose a UI section in the File Explorer page allowing one-click preview and restoration of historical snapshots.
  - Introduce automatic snapshot pruning policies (e.g., retain snapshots for 14 days or cap total snapshot storage size).

### 3.2 Enhanced Audit Trail Filtering & Exporting
- **Current State:** Audit logs are saved to append-only JSONL files and mirrored in SQLite, searchable via query text.
- **Recommendation:** Add explicit date range filtering, action-type dropdown filters, and one-click JSON/CSV export capabilities in the `/audit` control plane page.

---

## 4. Frontend & User Experience (Next.js / Tailwind)

### 4.1 Real-Time System Telemetry Dashboard
- **Current State:** `RateLimitBadge` displays basic rate status.
- **Recommendation:** Build a real-time system performance bar showing:
  - Active Ollama model name & memory footprint.
  - Active session execution time and token consumption rate (tokens/sec).
  - Background process status for sandbox executions.

### 4.2 Interactive Snapshot Explorer & Revert
- **Current State:** The `/files` page displays workspace files and file content previews.
- **Recommendation:** Add a "Snapshots & Backups" tab in the `/files` workspace view to allow developers to inspect pre-change state and perform target restorations without manually checking terminal logs.

---

## 5. Summary of Recommended Implementation Order

1. **Phase 1 (Completed in Current Iteration):** Snapshot listing API (`GET /api/snapshots`), snapshot metadata helper on `ToolRegistry`, and frontend Snapshot Explorer component.
2. **Phase 2 (Immediate Next Step):** Local vector embeddings using Ollama `/api/embed` and SQLite local vector storage.
3. **Phase 3 (Medium Term):** Adaptive token context budgeting and ReAct loop auto-summarization.
4. **Phase 4 (Long Term):** Multi-workspace isolation and enhanced command sandbox profiling.
