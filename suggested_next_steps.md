# Suggested Next Steps for Local Ollama Agent Harness

## Architecture & System Overview
The **Local Ollama Agent Harness** is a privacy-first, local-only coding and file agent. It pairs a Python (FastAPI) backend with a Next.js/Tailwind control plane. All LLM calls pass through a local Ollama daemon (`127.0.0.1:11434`), and file mutations / shell executions are tightly governed by a workspace sandbox, approval queue, and Linux `unshare` namespace isolation.

---

## 1. High-Priority Architectural & Feature Enhancements

### A. Local Semantic Vector Search & Retrieval (RAG)
- **Current State:** Search relies on `keyword_search` (case-insensitive substring match). `backend/app/indexing/embeddings.py` is currently a placeholder stub.
- **Proposed Enhancement:**
  - Implement native local embedding generation using Ollama's `POST /api/embeddings` endpoint (e.g. using `nomic-embed-text` or `all-minilm`).
  - Store vectors in SQLite using JSON arrays or `sqlite-vss` extension for vector storage and cosine similarity retrieval.
  - Expose a `semantic_search` tool to allow the agent to locate relevant functions and classes across large codebases without needing exact string matches.

### B. Extended Tooling & Language Support
- **Current State:** Tools cover filesystem read/write/delete, keyword search, basic Git status/log/diff, and sandboxed binary execution.
- **Proposed Enhancement:**
  - **LSP / AST Analysis:** Integrate lightweight AST parsing (Python `ast`, Tree-sitter) or Language Server Protocol (LSP) integrations for jump-to-definition, symbol resolution, and call graph analysis.
  - **Structured Code Formatting & Linting:** Add built-in formatting/linting tools (`ruff`, `prettier`, `eslint`) to automatically fix style issues after file edits.

### C. Advanced Session Management & Revert Capabilities
- **Current State:** Applied overwrites and deletes create pre-change snapshots in `.harness-snapshots`.
- **Proposed Enhancement:**
  - **Multi-turn Revert Stack:** Expose a full snapshot restoration interface in the Next.js control plane to let users revert to any arbitrary historical checkpoint across turns.
  - **Branch / Fork Session:** Allow users to branch a session at any turn to explore alternative agent implementation paths without losing previous progress.

---

## 2. Security, Isolation & Performance Improvements

### A. Non-Linux OS Isolation Fallback
- **Current State:** `EXEC_REQUIRE_OS_SANDBOX=true` requires Linux `unshare` namespaces. Non-Linux platforms (macOS/Windows) fail closed for command execution.
- **Proposed Enhancement:**
  - Implement a Docker / Podman container fallback adapter for macOS and Windows development environments so sandbox execution remains strict without requiring bare-metal Linux.

### B. Smart Token & Context Window Management
- **Current State:** Token budgeting truncates outputs and limits per-turn counts (`max_output_tokens_per_turn`, `max_total_tokens_per_session`).
- **Proposed Enhancement:**
  - Implement sliding-window prompt summarization: when session token length approaches model context capacity (`num_ctx`), summarize earlier tool outputs into compact turn memories to maintain long-running context.

---

## 3. Recommended Roadmap & Execution Plan

1. **Phase 1 (Immediate):** Implement local semantic search via Ollama `/api/embeddings`, SQLite vector indexing, and `semantic_search` tool integration.
2. **Phase 2 (Short-Term):** Expand Next.js UI with one-click snapshot reverts and session branching.
3. **Phase 3 (Medium-Term):** Add AST / Tree-sitter code navigation tools and multi-platform container sandboxing.
