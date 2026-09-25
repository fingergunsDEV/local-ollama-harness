# Suggested Next Steps for Local Ollama Agent Harness

This document outlines proposed architecture, security, feature, and usability improvements for the **Local Ollama Agent Harness**.

---

## 1. Local Semantic Search & Vector Embeddings (`backend/app/indexing/embeddings.py`)
- **Objective:** Enable true semantic search across indexed workspace files using the local Ollama `/api/embeddings` or `/api/embed` endpoint.
- **Implementation Details:**
  - Build `LocalEmbeddingEngine` in `backend/app/indexing/embeddings.py`.
  - Connect to `OllamaClient` to generate vector embeddings for indexed workspace code chunks.
  - Store vector embeddings locally in SQLite (`file_embeddings` table) alongside SHA-256 file content digests.
  - Compute cosine similarity in pure Python / SQLite query to find relevant code snippets for user queries.
  - Enforce `OllamaRateLimiter` and strict loopback validation on embedding generation requests.

---

## 2. Agent Tooling & Robustness Enhancements
- **Semantic Code Search Tool:**
  - Expose a `semantic_search(query: str, top_k: int = 5)` tool in `backend/app/tools/search_tools.py`.
  - Register `semantic_search` in `ToolRegistry` and `TOOL_SCHEMAS`.
- **ReAct Protocol Parsing Improvements:**
  - Enhance `_parse_react_action` in `orchestrator.py` to strip markdown code blocks (e.g., ````json ... ````) produced by smaller local models.
  - Support robust repair or retry prompts when JSON syntax errors occur.

---

## 3. Frontend UI / UX Improvements
- **Semantic Search & Vector Indexing Control:**
  - Add a "Semantic Indexing" status indicator and search query input in the file browser view.
- **Enhanced Visual Feedback & Telemetry:**
  - Display per-turn output tokens, generation speed (tokens/sec), and evaluation time.
  - Provide inline diff syntax highlighting and clear approval action badges.

---

## 4. Backend Safety & Sandbox Hardening
- **Namespace Sandbox Fallback Diagnostics:**
  - Improve error messages when Linux `unshare` is unavailable (e.g. non-Linux systems or restricted container runtimes) to clearly explain sandbox requirements.
- **Session Audit Export:**
  - Add API endpoint and UI action to export full session audit trails as JSON / CSV.

---

## 5. Comprehensive Test Coverage
- **Embedding & Semantic Search Tests:**
  - Unit tests verifying embedding generation, rate limiting compliance, and cosine similarity ranking in `backend/tests/test_embeddings.py`.
- **ReAct Markdown Stripping Tests:**
  - Unit tests verifying ReAct parser handles json wrapped in triple backticks and malformed inputs gracefully.
