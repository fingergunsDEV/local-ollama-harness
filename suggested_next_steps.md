# Suggested Next Steps: Local Ollama Agent Harness

## Executive Summary
The **Local Ollama Agent Harness** is a secure, loopback-restricted, approval-gated agent runtime designed for local workspace management and coding assistance. After a full scan of the codebase architecture (`backend/` FastAPI service and `frontend/` Next.js control plane), several key areas for expansion, performance optimization, and developer experience enhancement have been identified.

---

## 1. Toolset & Editing Capabilities

### 1.1 Targeted File Modifications (`replace_in_file`)
- **Current State:** The filesystem toolset currently only supports `write_file` (overwriting the whole file), `create_file`, and `delete_file`. Full file rewrites consume significant context tokens and increase diff noise for minor edits.
- **Recommendation:** Implement a targeted `replace_in_file` tool that performs exact string search-and-replace within a specified workspace file, generating unified diffs for approval and dry-run previewing.

### 1.2 Advanced Search & Pattern Matching (`regex_search`)
- **Current State:** `keyword_search` performs basic substring matching (`query.lower() in line.lower()`).
- **Recommendation:** Implement `regex_search` in `search_tools.py` supporting regular expressions, max match limits, and optional file inclusion/exclusion glob patterns.

### 1.3 Patch Application Tool (`apply_patch`)
- **Current State:** Unified diffs are rendered for approval, but multi-line diff patches cannot be directly applied by the model.
- **Recommendation:** Provide an `apply_patch` tool capable of parsing standard Unified Diff format (`--- a/file` / `+++ b/file`) to enable multi-hunk edits in a single tool call.

---

## 2. Local Semantic Search & Vector Embeddings

### 2.1 Ollama Vector Embeddings (`app/indexing/embeddings.py`)
- **Current State:** `embeddings.py` is currently an unconfigured placeholder module. Metadata indexing is purely file-stat and sha256-hash based in `indexer.py`.
- **Recommendation:** Implement `OllamaEmbeddings` using the local Ollama `/api/embed` endpoint to compute vector embeddings for chunked workspace files. Integrate vector search with cosine similarity while enforcing the local loopback policy and shared rate limiter.

### 2.2 Hybrid Code Search (`semantic_search`)
- **Current State:** Search relies strictly on exact text matching.
- **Recommendation:** Combine keyword/regex search results with dense vector retrieval (hybrid search with reciprocal rank fusion) for superior context discovery across large repositories.

---

## 3. Orchestrator & Context Management

### 3.1 Token Estimation & Dynamic Sliding Context Window
- **Current State:** `_fit_context` in `orchestrator.py` uses a crude character-length cap (`48_000` chars) to truncate past messages.
- **Recommendation:** Integrate precise tiktoken or model-specific token counting. Retain system prompt, key user goals, and latest file snapshots while summarizing intermediate tool interactions when approaching context limits.

### 3.2 Dynamic ReAct Repair & Self-Correction
- **Current State:** Non-native models receive ReAct suffix instructions and 1 retry on malformed JSON.
- **Recommendation:** Enhance JSON repair with fuzzy parsing and structured exception feedback when arguments fail Zod/Pydantic schema validation.

---

## 4. Frontend & User Experience

### 4.1 Interactive Diff Previewer & Hunk Approvals
- **Current State:** Diffs are displayed as preformatted raw text inside `ToolCallCard.tsx`.
- **Recommendation:** Integrate a side-by-side or unified interactive diff view with syntax highlighting, line numbers, and approval per hunk/file.

### 4.2 Audit Log Filtering & Export
- **Current State:** The Audit view displays a raw table of up to 80 recent entries.
- **Recommendation:** Add filtering by actor (`agent`/`user`), action type, status, and date range, alongside JSONL log export capabilities.

---

## 5. Security & Sandbox Enhancements

### 5.1 Fine-Grained Environment Sanitization & Resource Caps
- **Current State:** OS sandbox relies on Linux `unshare` namespaces for process isolation.
- **Recommendation:** Expose configurable resource limits (`cgroups` memory/CPU limits) and file-descriptor isolation for long-running executed tasks.
