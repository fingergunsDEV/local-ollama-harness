# Suggested Next Steps for Local Ollama Agent Harness

This document outlines recommended improvements and architectural enhancements for the **Local Ollama Agent Harness** based on a thorough scan of the backend and frontend codebase.

---

## 1. Local Semantic Search & Embedding Indexing (High Priority)
- **Current State:** `backend/app/indexing/embeddings.py` is currently a placeholder stub ("Semantic indexing is intentionally optional and disabled in v1"). Code search relies strictly on line-by-line keyword string matching in `backend/app/tools/search_tools.py`.
- **Proposed Improvement:**
  - Implement `OllamaEmbeddings` in `backend/app/indexing/embeddings.py` using Ollama's local `/api/embed` or `/api/embeddings` endpoint.
  - Upgrade `LocalIndexer` in `backend/app/indexing/indexer.py` to chunk text files, generate vector embeddings using a lightweight local model (e.g., `nomic-embed-text` or `all-minilm`), and store vectors/chunks in SQLite.
  - Implement a `semantic_search` tool in `backend/app/tools/search_tools.py` calculating cosine similarity over stored chunk embeddings.
  - Register `semantic_search` in `backend/app/tools/__init__.py` so the agent can discover code conceptually (e.g., "Find authentication middleware logic").

---

## 2. Multi-File Atomic Diff Preview & Application
- **Current State:** File edits are limited to single-file `write_file` or `delete_file` calls. Complex multi-file refactoring requires individual tool turns and separate approval dialogs for each file.
- **Proposed Improvement:**
  - Add a `apply_patch` / `multi_file_diff` tool capable of parsing standard Unified Diffs across multiple files.
  - Update `ApprovalManager` and frontend `ApprovalModal.tsx` to render multi-file diff previews in a single atomic review step.

---

## 3. Persistent Workspace Session Context & Memory Summarization
- **Current State:** `AgentOrchestrator._fit_context` uses a conservative naive character truncation strategy (48,000 characters) when message history grows large.
- **Proposed Improvement:**
  - Introduce dynamic token counting using `tiktoken` or Ollama's `num_ctx` metadata.
  - Implement sliding-window summarization when conversation context approaches token limits, preserving key system notes, file paths, and decisions in a compressed memory message.

---

## 4. Frontend Developer Experience & Workspace File Viewer
- **Current State:** `HarnessDashboard.tsx` provides basic file content viewing and streaming transcripts, but lacks diff highlighting, file tree navigation, and real-time status badges for local index status.
- **Proposed Improvement:**
  - Replace the flat file button list in `frontend/components/HarnessDashboard.tsx` with a collapsible file tree component.
  - Add syntax highlighting for code previews and visual unified diff rendering for tool execution previews.
  - Add a manual "Refresh Index" button and visual index progress indicator in the UI.

---

## 5. Linux Namespace Isolation Diagnostics & Fallbacks
- **Current State:** `backend/app/safety/sandbox.py` enforces Linux `unshare` namespaces when `EXEC_REQUIRE_OS_SANDBOX=true`, failing closed if namespaces are unsupported (e.g., in non-Linux or container environments without `CAP_SYS_ADMIN`).
- **Proposed Improvement:**
  - Provide a detailed diagnostic health check endpoint (`/api/sandbox/check`) detailing why `unshare` is or is not available.
  - Provide clear user instructions in `README.md` and settings UI regarding container capabilities required (`--cap-add=SYS_ADMIN`).

---

## 6. Comprehensive Test Suite Expansion
- **Current State:** Tests cover core sandbox boundaries, allowlists, rate limits, and basic dry-runs.
- **Proposed Improvement:**
  - Add test suites for semantic embeddings, vector index persistence, similarity search, SSE streaming error recovery, and React agent protocol fallback parsing.
