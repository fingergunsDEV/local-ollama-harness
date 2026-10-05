# Suggested Next Steps & Codebase Analysis

## 1. Executive Summary
The **Local Ollama Agent Harness** is a robust, privacy-focused coding agent harness designed to run strictly against a local Ollama daemon and a sandboxed workspace directory. It features strong security controls including workspace path canonicalization, dry-run diff previews, approval-gated mutations, Linux namespace sandboxing for command execution, rate limiting, and structured audit logging.

This document outlines key technical findings and recommendations for evolving the harness to improve performance, usability, intelligence, and reliability.

---

## 2. Technical Audit & Key Findings

### A. Search & Indexing Capabilities
- **Current State:** `SearchTools.keyword_search` performs a pure-Python string match across files in the workspace. However, unlike `LocalIndexer`, `SearchTools` does not respect `.gitignore` or `.harnessignore` patterns, resulting in unnecessary scans of `__pycache__`, `.venv`, `node_modules`, and snapshot directories.
- **Embeddings Placeholder:** `backend/app/indexing/embeddings.py` is currently a stub file with notes that semantic indexing is optional and reserved for a local Ollama `/api/embeddings` implementation.

### B. File Snapshot & Reversion Engine
- **Current State:** The backend API exposes `POST /api/snapshots/restore` and the README references `.harness-snapshots` for pre-change snapshot storage. However, `FileTools.write_file`, `create_file`, and `delete_file` do not automatically create pre-mutation snapshots in `.harness-snapshots` when applying live edits.
- **Gap:** Restoring previous states relies on manual snapshot creation or external mechanisms.

### C. Context Window & Token Management
- **Current State:** Basic token budget limits (`RunBudget`) exist, but conversation history expansion during multi-turn orchestration can exceed model context limits if context window pruning/summarization is not active.

### D. Process Isolation & Execution Feedback
- **Current State:** Command execution relies on Linux `unshare` namespaces (`EXEC_REQUIRE_OS_SANDBOX=true`). Streaming stderr/stdout live back to the orchestrator during long-running tasks provides better visibility.

---

## 3. Recommended Roadmap & Next Improvements

### Phase 1: Search & File Management Enhancements (High Priority)
1. **Ignore-Aware Keyword Search:**
   - Integrate `GitIgnoreSpec` into `SearchTools.keyword_search` so `.gitignore`, `.harnessignore`, `.git/`, and binary/snapshot folders are automatically filtered out during searches.
2. **Automatic Pre-Mutation Snapshots:**
   - Update `FileTools` write and delete methods to capture pre-change content into `.harness-snapshots` with unique SHA256/timestamp IDs before executing non-dry-run mutations.

### Phase 2: Local Semantic Search with Ollama Embeddings (High Priority)
1. **Local Ollama Embeddings Engine:**
   - Implement `OllamaEmbeddings` in `backend/app/indexing/embeddings.py` using Ollama's local `/api/embeddings` (or `/api/embed`) endpoint.
   - Route embedding requests through `OllamaRateLimiter` to protect local hardware.
   - Implement cosine similarity vector search stored in local SQLite (`file_embeddings` table).

### Phase 3: Agent Orchestration & Frontend Quality of Life (Medium Priority)
1. **Context Compaction & Summarization:**
   - Auto-summarize old tool outputs when token consumption reaches 75% of context limit.
2. **Enhanced UI Approval Workflow:**
   - Add inline diff highlighting and batch approval capability in Next.js `HarnessDashboard`.

---

## 4. Immediate Implementation Plan (Completed)
- [x] Create `suggested_next_steps.md` with comprehensive findings.
- [x] Implement `.gitignore` / `.harnessignore` filtering in `SearchTools`.
- [x] Implement local Ollama embeddings client in `backend/app/indexing/embeddings.py`.
- [x] Implement automatic pre-mutation file snapshotting in `FileTools`.
- [x] Add comprehensive test coverage for search filtering, embeddings, and pre-mutation snapshots.
- [x] Verify backend pytest suite and frontend Next.js production build.
