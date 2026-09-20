# Suggested Next Steps for Local Ollama Agent Harness

## Executive Overview
The **Local Ollama Agent Harness** provides a secure, local-only runtime for autonomous coding agent execution with explicit user approvals, sandboxed process execution via Linux namespaces, rate limiting, and an append-only audit log.

After a thorough scan of the codebase, several key areas have been identified for enhancement, optimization, and feature expansion to improve search accuracy, agent autonomy, performance, and user experience.

---

## Codebase Analysis & Findings

### 1. Strengths & Security Posture
- **Strict Workspace Sandboxing:** Paths are canonicalized with `os.path.realpath`, preventing directory traversal and symlink escapes.
- **Loopback Validation:** `OllamaClient` enforces local loopback addresses unless explicitly overridden via `ALLOW_REMOTE_OLLAMA=true`.
- **Command Sandboxing:** Execution requires Linux `unshare` namespaces (user, mount, network, PID) with a scrubbed environment and restricted binary allowlist.
- **Approval & Audit Pipeline:** Dry run mode by default, persisted approval gates, and append-only JSONL / SQLite audit records.

---

## Prioritized Suggested Improvements

### Priority 1: Local Semantic Embeddings & Vector Search (High Impact)
* **Current State:** `backend/app/indexing/embeddings.py` is an empty stub noted as "intentionally optional and disabled in v1".
* **Proposed Enhancement:**
  - Implement an `OllamaEmbeddings` client in `backend/app/indexing/embeddings.py` using Ollama's local `/api/embed` endpoint.
  - Compute normalized embedding vectors and cosine similarity scores for text chunks within the workspace.
  - Extend `backend/app/tools/search_tools.py` to support semantic hybrid search (combining exact keyword regex matching with vector similarity search).
  - Provide automatic fallback to keyword search when embedding models (e.g., `nomic-embed-text`, `all-minilm`) are not available on the local Ollama instance.

### Priority 2: Structured Document & Code Chunking in Indexer
* **Current State:** `backend/app/indexing/indexer.py` computes SHA-256 digests and metadata for whole files up to `max_files_indexed`.
* **Proposed Enhancement:**
  - Implement line-based and AST/syntax-aware chunking for file indexing.
  - Store vector embeddings of code chunks directly in SQLite (`file_chunks` table).
  - Enable fast semantic context retrieval for the orchestrator during task execution.

### Priority 3: Enhanced ReAct Protocol & Fault-Tolerant JSON Parsing
* **Current State:** Non-native models use a single ReAct JSON protocol (`{"action": "...", "arguments": {...}}`). If output is malformed, a simple prompt correction is sent back.
* **Proposed Enhancement:**
  - Add robust JSON repair heuristics (e.g., stripping markdown code block fences ` ```json ... ``` ` or extracting embedded JSON blocks).
  - Support multi-step execution plans and execution budget auto-scaling based on task complexity.

### Priority 4: Audit Trail Export & Snapshot UI Management
* **Current State:** Audit logs are saved in SQLite / JSONL and displayed in `frontend/components/HarnessDashboard.tsx`.
* **Proposed Enhancement:**
  - Add API endpoints to export audit entries as JSON / CSV.
  - Provide visual snapshot comparison / diff view in the frontend for restored snapshots.

---

## Action Plan for Immediate Implementation
1. **Implement `backend/app/indexing/embeddings.py`**:
   - `OllamaEmbeddings` class interacting with `OllamaClient` `/api/embed`.
   - Vector normalization and cosine similarity score calculation.
2. **Upgrade `backend/app/tools/search_tools.py` & `backend/app/main.py`**:
   - Add semantic search method to `SearchTools`.
   - Graceful fallback when local embedding model is offline or uninstalled.
3. **Add Comprehensive Tests**:
   - Test suite in `backend/tests/test_embeddings.py` covering embedding generation, cosine similarity, and search fallback.
