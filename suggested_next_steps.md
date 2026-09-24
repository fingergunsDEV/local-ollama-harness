# Suggested Next Steps & System Enhancements

## 1. Executive Summary
The **Local Ollama Agent Harness** provides a robust, local-only, approval-gated runtime environment for LLM-driven coding agents. Based on a comprehensive audit of the backend architecture, tool execution sandbox, and orchestrator loop, this document outlines prioritized improvements to enhance reliability, performance, tool capabilities, and model compatibility without compromising safety boundaries.

---

## 2. Recommended Improvements

### 2.1 Orchestrator & ReAct Parser Reliability
- **Markdown-Fence Cleaning in ReAct Parser**: Models lacking native tool calling (e.g. smaller Llama 3 / Mistral variants) often output JSON wrapped in markdown code fences (` ```json ... ``` `) or with surrounding conversational text. Updating `_parse_react_action` to strip markdown fences and extract JSON objects prevents unnecessary retry turns.
- **Dynamic Context Window Fitting**: Replace the fixed 48,000-character context limit with a dynamic character budget calculated from model capabilities (`context_length` retrieved from Ollama `/api/show`).

### 2.2 Workspace Search Efficiency
- **Ignore Pattern Filtering in Keyword Search**: `SearchTools.keyword_search` currently traverses every file under the search directory using `rglob("*")`, including `node_modules`, `.venv`, `.git`, and build outputs. Integrating `GitIgnoreSpec` (from `.gitignore` and `.harnessignore`) into `keyword_search` drastically reduces search latency and avoids hitting result truncations on vendor files.

### 2.3 Extended File Operations (`move_file` & `copy_file`)
- **File Relocation & Duplication**: Add `move_file` and `copy_file` tools in `fs_tools.py` with full sandbox path validation, dry-run action plans, pre-change snapshot backups, and approval checks.

### 2.4 Local Semantic Embeddings & Search
- **Local Embedding Generation**: Implement `embed` in `ollama_client.py` targeting Ollama's `/api/embed` endpoint, managed under `OllamaRateLimiter`.
- **Semantic Vector Search**: Implement `LocalEmbeddings` in `backend/app/indexing/embeddings.py` and expose `semantic_search` in `search_tools.py` for similarity searching over indexed workspace file chunks.

### 2.5 Enhanced Test Coverage
- Add comprehensive test suites in `backend/tests/` verifying ReAct parsing edge cases, search ignore filtering, file move/copy sandbox limits, and embedding client behavior.

---

## 3. Phased Implementation Plan

| Phase | Description | Key Deliverables |
| --- | --- | --- |
| **Phase 1** | Orchestrator & Search Enhancements | ReAct markdown code block extraction; `.gitignore` aware keyword search. |
| **Phase 2** | Extended File Operations | `move_file` and `copy_file` tools in `fs_tools.py` & registry schemas. |
| **Phase 3** | Local Embeddings & Semantic Search | `OllamaClient.embed()`, `LocalEmbeddings`, and `semantic_search` tool. |
| **Phase 4** | Test Verification | pytest unit test suite passing 100%. |
