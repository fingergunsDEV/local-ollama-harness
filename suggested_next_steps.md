# Suggested Next Steps for Local Ollama Agent Harness

After scanning the codebase, the architecture, safety controls, and test suites, we have identified key areas for improvement. The harness has an excellent security foundation (loopback Ollama enforcement, dry-run approvals, Linux namespace command sandboxing, strict workspace root canonicalization).

Below are the recommended next steps to elevate the system's capabilities, performance, and developer experience while preserving its zero-trust local security posture.

---

## 1. Advanced Search & Local Embeddings Architecture (Priority: High)

### 1.1 Local Semantic Embeddings & Vector Search
- **Current State:** `backend/app/indexing/embeddings.py` is a placeholder stating semantic indexing is disabled in v1.
- **Improvement:**
  - Implement native Ollama `/api/embeddings` or `/api/embed` integration in `OllamaClient` using a configurable embedding model (e.g., `nomic-embed-text` or `all-minilm`).
  - Store vector embeddings in SQLite (using sqlite-vec or a lightweight blob vector storage with cosine similarity calculation in Python/SQLite).
  - Add a `semantic_search` tool to `SearchTools` so the model can retrieve code based on concept rather than exact string matching.

### 1.2 Regex & File Pattern Filtering in Keyword Search
- **Current State:** `SearchTools.keyword_search` performs a case-insensitive substring match across all files.
- **Improvement:**
  - Add optional `is_regex` boolean flag for regex pattern matching.
  - Add `file_pattern` / `include_ext` filters (e.g., `*.py`, `*.ts`) to limit search scope and reduce unnecessary file reads.

---

## 2. Expanded Git Tooling & Safety Controls (Priority: Medium)

### 2.1 Extended Read-Only & Local Git Operations
- **Current State:** `GitTools` currently supports diff generation, commit creation, and checkout.
- **Improvement:**
  - Add `git_status` tool to show untracked, modified, and staged files before committing.
  - Add `git_create_branch` / `git_checkout_branch` for local feature branch creation without allowing remote push/fetch operations.
  - Ensure all git mutation operations continue to respect the dry-run and approval workflows.

---

## 3. Resilience, Rate Limiting & Streaming (Priority: Medium)

### 3.1 Model Load & Timeout Handling
- **Current State:** Cold model preloading or large model load times can cause timeouts if the first chunk takes longer than expected.
- **Improvement:**
  - Add dedicated handling for model loading status events during Ollama streaming.
  - Provide a visual "Loading model into memory..." indicator in the SSE event pipeline and frontend UI.

### 3.2 Granular Token Budgeting per Context Window
- **Current State:** `AgentOrchestrator` uses a fixed 48k character truncation budget (`_fit_context`).
- **Improvement:**
  - Dynamically query model context size from `/api/show` capability response and set token budgets dynamically per session.

---

## 4. Frontend & UI/UX Enhancements (Priority: Medium)

### 4.1 Enhanced Diff Rendering & Syntax Highlighting
- **Current State:** Plain text unified diff view in tool call cards.
- **Improvement:**
  - Add syntax-highlighted side-by-side or inline unified diff view for file modifications and proposed writes.

### 4.2 Interactive Approval & Audit Filtering
- **Current State:** Audit view supports simple text queries; approvals are listed in sequence.
- **Improvement:**
  - Add action-type filter tags (e.g., `write`, `exec`, `git_commit`) and status filters (`approved`, `denied`, `pending`) in both UI pages.

---

## 5. Automated Testing & Verification Strategy (Priority: High)

### 5.1 Test Coverage Expansion
- Add unit tests for vector similarity search, regex search filtering, and Ollama embedding API error handling.
- Add end-to-end SSE event stream simulation tests in FastAPI test suite.
