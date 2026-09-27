# Suggested Next Steps for Local Ollama Agent Harness

Based on a comprehensive scan of the Local Ollama Agent Harness codebase, the following architectural enhancements and feature improvements are recommended to extend the harness's capabilities while maintaining its core safety posture and local-only constraints.

---

## 1. Local Semantic Code Search & Vector Indexing (High Priority)
* **Current State:** `backend/app/indexing/embeddings.py` is currently a stub placeholder noting that semantic indexing is optional.
* **Proposed Enhancement:**
  - Implement a `LocalEmbeddings` client leveraging Ollama's local `/api/embed` endpoint (e.g., using models like `nomic-embed-text` or `all-minilm`).
  - Extend `SessionStore` SQLite schema to store chunked vector embeddings for indexed workspace files.
  - Expose a `semantic_search` tool in `search_tools.py` that computes cosine similarity against stored vectors to perform concept-based code search across the workspace.

---

## 2. Snapshot History Browsing & UI Rollback (Medium Priority)
* **Current State:** Applied file mutations create pre-change snapshots in `.harness-snapshots/`, and `/api/snapshots/restore` handles restoring a single snapshot, but there is no list/history endpoint or UI component to inspect past snapshots.
* **Proposed Enhancement:**
  - Add `GET /api/snapshots` to return chronological snapshot entries with metadata (file path, snapshot ID, timestamp, sha256).
  - Add a "File Snapshots & Revert" tab in the Next.js control plane to display unified diffs between current file state and previous snapshots with a one-click restore button.

---

## 3. Session Branching & Multi-Turn Checkpoints (Medium Priority)
* **Current State:** Sessions are stored sequentially in SQLite, and interrupting or modifying past turns requires starting a new session.
* **Proposed Enhancement:**
  - Support session branching (`POST /api/sessions/{id}/branch`) at specific turn checkpoints.
  - Allow users to fork an agent loop to explore alternative execution paths or retry a denied action without losing previous context.

---

## 4. Custom Declarative Tools & Webhook Gateway (Low Priority)
* **Current State:** Tools are statically registered in `ToolRegistry` (`fs_tools`, `search_tools`, `git_tools`, `exec_tools`).
* **Proposed Enhancement:**
  - Support user-configurable declarative tool schemas in `.harness/tools.json` (e.g., local REST endpoints or custom scripts).
  - Enforce strict JSON Schema validation and approval gates for all user-defined custom tools.

---

## 5. Non-Linux Sandbox Emulation & Improved Error Guidance
* **Current State:** Command execution relies on Linux `unshare` namespaces (`EXEC_REQUIRE_OS_SANDBOX=true`). On systems without Linux user namespaces, execution fails closed with a generic error.
* **Proposed Enhancement:**
  - Provide actionable UI diagnostic messages explaining why `unshare` is unavailable (e.g., running on macOS/Docker/Windows) and guide the user on environment configuration.
