# Suggested Next Steps for Local Ollama Agent Harness

## Codebase Scan Findings & Analysis

During an analysis of the repository, the following strengths and areas for improvement were identified across the Python (FastAPI) backend and Next.js control plane:

### Strengths
1. **Strict Local-Only Security Model**: `OllamaClient` enforces loopback IP validation (`127.0.0.1`, `::1`) by default and ignores HTTP environment proxies (`trust_env=False`).
2. **Robust Sandboxing & Dry-Run Controls**: `WorkspaceSandbox` prevents path traversal, symlink escapes, null bytes, and sensitive file reads (`.env`, `.git/config`).
3. **OS-Level Execution Isolation**: Command execution leverages a Linux namespace `unshare` adapter for process isolation.
4. **Auditability & Approval Gates**: All user and agent actions are persisted in SQLite and append-only JSONL logs.

### Key Areas for Improvement

#### 1. Tool Registry & Schema Alignment
* **Issue**: `stat_file` handler exists in `ToolRegistry._handlers` (`backend/app/tools/__init__.py`), but is omitted from `TOOL_SCHEMAS`.
* **Impact**: Native tool-calling Ollama models cannot discover or call `stat_file`.
* **Recommendation**: Add `stat_file` schema definition to `TOOL_SCHEMAS`.

#### 2. Vector Indexing & Local Embeddings Support
* **Issue**: `backend/app/indexing/embeddings.py` is currently a stub file with no active code, while `LocalIndexer` in `backend/app/indexing/indexer.py` handles basic file metadata indexing.
* **Impact**: Semantic search capabilities remain ungrounded.
* **Recommendation**: Extend `OllamaClient` with an `/api/embed` endpoint caller and implement `LocalEmbeddings` generator in `backend/app/indexing/embeddings.py` using local Ollama embedding models (e.g. `nomic-embed-text`) subject to the `OllamaRateLimiter`.

#### 3. Frontend Error Handling & SSE Resilience
* **Issue**: EventSource / fetch stream reconnects in `HarnessDashboard.tsx` can lose intermediate token events if network drops mid-stream.
* **Recommendation**: Implement client-side event buffering and stream session state resumption markers.

#### 4. Extended Test Coverage
* **Issue**: Unit tests do not cover embedding features or `stat_file` tool call schemas.
* **Recommendation**: Add dedicated test suites in `backend/tests/test_embeddings.py`.

---

## Action Plan for Immediate Enhancements

1. **Schema Alignment**: Add `stat_file` tool definition to `TOOL_SCHEMAS`.
2. **Local Embeddings Integration**: Implement `/api/embed` method in `OllamaClient` and `LocalEmbeddings` class.
3. **Automated Testing**: Add pytest suite verifying `stat_file` tool schema and local embeddings client methods.
4. **Build & Test Verification**: Execute `pytest` and `npm run build` to confirm zero regressions.
