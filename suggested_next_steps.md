# Suggested Next Steps for Local Ollama Agent Harness

This document outlines key technical analysis, architectural recommendations, security enhancements, performance optimizations, and feature enhancements for the Local Ollama Agent Harness codebase.

---

## 1. Executive Summary & Codebase Review

The **Local Ollama Agent Harness** is a local-only, approval-gated coding and file agent system designed with security and strict boundaries at its core:
- **Security & Sandboxing:** Strict workspace scoping using canonical path resolution (`WorkspaceSandbox`), Linux `unshare` namespace isolation for command execution (`ExecTools`), command allowlisting, and rejection of sensitive target paths (e.g., `.env`, `.git/config`).
- **Control & Approvals:** Dual-mode execution (Dry-run ON by default), interactive approval gates for file/command mutations, and server-side run budget limits (`RunBudget`).
- **Ollama Integration:** Strict loopback URL validation (`OllamaClient`), shared token bucket rate limiting, and capabilities probing for native tools vs. ReAct mode.
- **Audit & Persistence:** Dual audit trail (redacted JSONL + SQLite database) tracking every user and agent action.

---

## 2. Technical Debt & Code Architecture Improvements

### 2.1 Modularity & Extensibility
1. **Tool Parameter Parsing & Validation:**
   - Current tool arguments rely on basic Python dict checks. Introducing strict Pydantic models for tool inputs across `fs_tools`, `git_tools`, and `exec_tools` will improve type safety and schema generation.
2. **Streaming & SSE Protocol Standardization:**
   - Standardize event shapes in `streaming.py` with typed schemas to facilitate frontend client typing.

### 2.2 Error Taxonomy & Resilience
1. **Granular Ollama Connection Errors:**
   - Categorize Ollama failure states into distinct sub-classes (e.g. `OllamaOffline`, `OllamaModelNotFound`, `OllamaTimeout`, `OllamaCORSBlocked`) to provide actionable UI guidance.
2. **Automatic Retry with Exponential Backoff:**
   - Implement transient error retry logic on `OllamaClient` generation requests without breaching token bucket rate limits.

---

## 3. Security & Safety Enhancements

1. **Path-Traversal Red-Teaming & Fuzzing Expansion:**
   - Expand `test_sandbox.py` to cover additional OS-specific edge cases, unicode normalized path tricks, and multi-hop symlink cycles.
2. **Sensitive Field & Secret Masking in Tool Output:**
   - Add automated regex sanitization to scrub API keys, bearer tokens, or password strings from tool outputs before storing them in session message history and audit logs.
3. **Environment Scrubbing for Exec Adapter:**
   - Ensure `unshare` process environments scrub all system secrets while maintaining mandatory paths like `PATH` and `LANG`.

---

## 4. Performance & Scalability Optimizations

1. **File Indexing & Hashing Performance:**
   - In `indexer.py`, file metadata hashing currently processes entire files synchronously. Parallelizing chunked hashing or utilizing file modification time cache keys will accelerate refresh on large workspaces.
2. **Context Window Token Budgeting:**
   - Move from character-length estimation (`48,000` chars in `_fit_context`) to token-aware counting or model-specific context limits provided by `/api/show` capability probes.

---

## 5. Key Feature Roadmaps (v1.1 & Beyond)

### 5.1 Local Semantic Search & Embedding Engine
- **Ollama Embedding Integration (`/api/embed`):**
  - Implement a zero-cloud local embedding pipeline using Ollama models (e.g. `nomic-embed-text` or `all-minilm`).
  - Store vector embeddings in local SQLite with cosine similarity calculations.
  - Expose a `semantic_search` tool in `search_tools.py` for context retrieval over large codebases.

### 5.2 Advanced Search Tools
- **Regex & Glob Pattern Search:**
  - Add a `regex_search` tool supporting full regular expressions and file pattern globbing (`*.py`, `*.tsx`).

### 5.3 Session Analytics & Telemetry Dashboard
- **Session Stats & Resource Usage Metrics:**
  - Provide `/api/sessions/{session_id}/stats` and `/api/stats` endpoints exposing token usage, total iterations, tool invocation counts, and wall-clock execution metrics.

---

## 6. Action Plan for Immediate Implementation

1. **Local Vector Search & Embeddings Engine:** Add `/api/embed` to `OllamaClient`, build `EmbeddingManager` in `embeddings.py`, and update `LocalIndexer`.
2. **Enhanced Search Tools:** Implement `semantic_search` and `regex_search` in `search_tools.py` and expose them in `TOOL_SCHEMAS`.
3. **Session Analytics & Telemetry API:** Add session usage aggregation queries in `session_store.py` and expose HTTP endpoints in `main.py`.
4. **Comprehensive Test Suite:** Write new unit and integration tests covering vector search, regex matching, and analytics endpoints.
