# Suggested Next Steps for Local Ollama Agent Harness

This document outlines key observations from a full codebase scan across `backend/` and `frontend/`, categorized by architectural areas, technical debt, and recommended feature enhancements.

---

## 1. Architectural Overview & Current Status

The **Local Ollama Agent Harness** is built with strong security-first constraints:
- **Loopback Enforcement:** Validates Ollama endpoints to ensure no external AI providers are reached without explicit operator override (`ALLOW_REMOTE_OLLAMA`).
- **Sandbox Controls:** Workspace boundary canonicalization with `os.path` and descendant checks preventing directory traversal.
- **Dry-run & Approval Gates:** All non-read-only file or shell actions generate diffs/plans and require SQLite-persisted approvals unless remembered or explicitly auto-approved.
- **Resource Budgeting:** `RunBudget` enforces strict limits on iterations, wall-clock time, per-turn output tokens, total session tokens, and file mutation sizes.

---

## 2. Identified Improvement Opportunities

### A. Local Semantic Search & Indexing Expansion (High Priority)
* **Current State:** `backend/app/indexing/embeddings.py` is currently a placeholder module stating semantic indexing is disabled in v1. `LocalIndexer` only indexes basic file metadata (SHA256, mtime, size) in SQLite.
* **Recommendation:** Implement a local embeddings client using Ollama's `POST /api/embed` (or `POST /api/embeddings`) endpoint. Embed file chunks and store them in a local SQLite vector table (`sqlite-vss` or cosine distance in Python) to enable semantic code search (`semantic_search` tool) alongside keyword search.

### B. Ignore-Pattern Aware Keyword Search
* **Current State:** `SearchTools.keyword_search` traverses directories using `rglob("*")` without checking `.gitignore` or `.harnessignore` patterns. As a result, searching large repositories can inadvertently scan build artifacts, `node_modules`, or virtual environments.
* **Recommendation:** Integrate `pathspec` (already used in `LocalIndexer`) into `SearchTools.keyword_search` to automatically exclude ignored paths and speed up search performance.

### C. Context Window & Token Budgeting Precision
* **Current State:** `AgentOrchestrator._fit_context` uses a fixed conservative character threshold (`48,000` chars) to truncate chat history.
* **Recommendation:** Leverage `client.capabilities(model)` to read `context_length` and dynamically adjust token estimation/truncation based on model capabilities and tokenizers.

### D. Frontend Resilience & UX Enhancements
* **Current State:** The Next.js frontend (`HarnessDashboard.tsx`) renders SSE streams and manages state directly.
* **Recommendation:**
  1. Add React Error Boundaries around major UI panes (Chat, Workspace Browser, Approval Queue).
  2. Improve SSE reconnect logic with exponential backoff on transient connection drops.
  3. Add dark/light mode toggle consistency and accessibility (aria-labels) on approval action buttons.

### E. Extended Test Coverage & Mock Harness
* **Current State:** Tests in `backend/tests/` verify sandbox, allowlist, dry-run, approval flow, and rate limiter, but rely heavily on standard fixtures.
* **Recommendation:** Add explicit test suites for embedding generation (`test_embeddings.py`) and mock Ollama HTTP streaming edge cases (e.g. abrupt disconnects during SSE).

---

## 3. Prioritized Implementation Roadmap

1. **Phase 1 (Immediate Scope):**
   - Implement `OllamaClient.embeddings` and `EmbeddingService` in `backend/app/indexing/embeddings.py`.
   - Update `SearchTools.keyword_search` in `backend/app/tools/search_tools.py` to respect `.gitignore` / `.harnessignore`.
   - Add unit tests for embeddings and ignore-aware search in `backend/tests/`.

2. **Phase 2 (Future Extensions):**
   - Implement vector table storage in SQLite for semantic chunk lookup.
   - Dynamic context window calculation in `AgentOrchestrator`.
   - Frontend Error Boundaries & SSE reconnect polish.
