# Suggested Next Steps: Local Ollama Agent Harness

## Executive Summary & Codebase Architecture Scan

The **Local Ollama Agent Harness** is a privacy-first, local-only developer agent platform built on FastAPI and Next.js. It features a strict security boundary enforcing loopback-only Ollama interaction, workspace sandbox canonicalization, argv allowlists with Linux namespace adapters (`unshare`), dry-run preview before file mutation, and server-side run budget limits.

A thorough scan of the codebase reveals a robust foundation with clean separation of concerns:
- `backend/app/orchestrator.py`: Manages the agent loop, tool call dispatching, SSE streaming events, and ReAct fallback.
- `backend/app/ollama_client.py`: Handles HTTP streaming with loopback validation and token bucket rate limiting.
- `backend/app/safety/`: Enforces path safety (`sandbox.py`), binary allowlists (`allowlist.py`), session limits (`limits.py`), rate limits (`rate_limiter.py`), and approvals (`approval.py`).
- `backend/app/indexing/`: Contains metadata indexing (`indexer.py`) and a stubbed embeddings module (`embeddings.py`).
- `frontend/components/`: Provides Next.js / React components for chat, dry-run toggle, tool call rendering, and approval queue management.

---

## Suggested Improvement Areas

### 1. Robust ReAct Parsing & Markdown Extraction (High Priority)
- **Current State:** `AgentOrchestrator._parse_react_action` attempts direct `json.loads(text.strip())`.
- **Gaps:** Many open-weights local Ollama models (e.g., Llama 3, Mistral, Qwen) output JSON enclosed in markdown code fences (e.g. ```json ... ```) or prefix JSON responses with brief explanatory text. When direct `json.loads` fails, the model receives an error turn, consuming budget.
- **Proposed Solution:** Implement flexible JSON extraction that checks for markdown code blocks (```json or ```) and extracts valid JSON objects within text preambles/postambles before falling back to error turns.

### 2. Local Semantic Embeddings & Vector Indexing (High Priority)
- **Current State:** `backend/app/indexing/embeddings.py` is a placeholder ("Semantic indexing is intentionally optional and disabled in v1").
- **Gaps:** File search currently relies on keyword/exact matching in `search_tools.py` and file path indexing in `indexer.py`.
- **Proposed Solution:** Implement `OllamaEmbeddings` using Ollama's local `/api/embeddings` or `/api/embed` endpoint. Compute vector embeddings for indexed workspace code chunks using local model defaults (e.g., `nomic-embed-text` or model-provided embeddings), obeying the loopback-only policy and shared `OllamaRateLimiter`.

### 3. File Snapshot & Revert API Enhancements (Medium Priority)
- **Current State:** File overwrites and deletes capture pre-change snapshots in `.harness-snapshots/`. `POST /api/snapshots/restore` handles restoration.
- **Gaps:** There is no endpoint to list available snapshots for a given path or session, making UI discovery manual.
- **Proposed Solution:** Add snapshot metadata discovery endpoints and ensure snapshot restoration produces detailed audit logs.

### 4. Re-usable Client Helper & Stream Diagnostics (Medium Priority)
- **Current State:** SSE stream parser in frontend receives structured JSON lines.
- **Gaps:** Network glitches or premature model disconnects surface generic errors.
- **Proposed Solution:** Add detailed stream disconnect recovery and diagnostic error codes in `streaming.py` and `ollama_client.py`.

---

## Action Plan for Implementation

1. **ReAct Parser Refactoring (`backend/app/orchestrator.py`)**:
   - Extract JSON objects from markdown triple-backtick fences (` ```json ` or ` ``` `).
   - Use regex or structural extraction to identify top-level JSON objects containing `action` or `final` keys even when surrounded by text.
   - Unit test with various local model output formats.

2. **Local Embeddings Implementation (`backend/app/indexing/embeddings.py`)**:
   - Create `OllamaEmbeddingClient` supporting `/api/embeddings`.
   - Implement cosine similarity calculation and memory/SQLite vector storage for workspace code chunks.
   - Integrate vector search into `search_tools.py` or indexing workflows.

3. **Backend Test Suite Expansion (`backend/tests/`)**:
   - Add unit tests for ReAct markdown parsing in `test_orchestrator.py`.
   - Add unit tests for local embedding generation and vector search in `test_embeddings.py`.

4. **Verification & Regression Testing**:
   - Ensure all backend tests (`python3 -m pytest`) pass cleanly.
   - Ensure frontend production build (`npm run build`) builds cleanly.
