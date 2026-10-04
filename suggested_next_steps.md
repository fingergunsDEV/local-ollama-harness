# Suggested Next Steps for Local Ollama Agent Harness

This document outlines key technical improvements and feature additions for the Local Ollama Agent Harness project.

## 1. Local Semantic Search via Ollama Embeddings (`app/indexing/embeddings.py` & `app/tools/search_tools.py`)
- **Objective**: Implement local embedding generation and semantic code search without external cloud dependencies.
- **Details**:
  - Implement `OllamaEmbedder` in `app/indexing/embeddings.py` using Ollama's `/api/embed` or `/api/embeddings` endpoint.
  - Ensure all embedding calls pass through `OllamaRateLimiter` and respect loopback security policies.
  - Store chunk embeddings in an `index_embeddings` SQLite table in `SessionStore`.
  - Add a `semantic_search` tool in `app/tools/search_tools.py` and register it in `ToolRegistry` and `TOOL_SCHEMAS`.

## 2. Session Transcript & Audit Log Exporting (`app/db/session_store.py` & `app/main.py`)
- **Objective**: Enable single-click exporting of complete session history (transcript, tool calls, approvals, and audit log entries) into Markdown and JSON formats.
- **Details**:
  - Add export formatting methods `export_session_markdown` and `export_session_json` to `SessionStore`.
  - Add `GET /api/sessions/{session_id}/export` endpoint to `app/main.py`.

## 3. Extended File Operations & Glob Filtering (`app/tools/fs_tools.py`)
- **Objective**: Enhance workspace file inspection capabilities.
- **Details**:
  - Support `pattern` (glob matching) in `list_files` to filter files by extension (e.g., `*.py`, `*.tsx`).
  - Add `create_directory` tool with sandbox validation and dry-run plan generation.

## 4. Smart Context Budgeting & Compaction (`app/orchestrator.py`)
- **Objective**: Improve model context utilization for long agent sessions.
- **Details**:
  - Enhance `_fit_context` in `AgentOrchestrator` to preserve system instructions and recent conversation turns while compacting older tool observations.

## 5. Automated Verification & Test Coverage (`backend/tests/`)
- **Objective**: Maintain 100% test pass rate across unit and integration tests for all newly added endpoints, tools, and storage methods.
