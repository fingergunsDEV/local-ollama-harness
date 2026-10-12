# Suggested Next Steps and Improvements

This document outlines recommended improvements and strategic enhancements for the **Local Ollama Agent Harness**. The recommendations focus on developer productivity, safety enforcement, local semantic indexing, frontend user experience, and testing rigor.

---

## 1. Agent Tools & Workspace Capabilities

### 1.1 Multi-File Batch Operations (`batch_read_files`)
* **Current Limitation:** The agent must issue individual `read_file` tool calls sequentially to inspect multiple workspace files, causing unnecessary LLM turns and token overhead.
* **Proposed Enhancement:** Introduce a `batch_read_files` tool that accepts an array of file paths and returns their text contents (subject to per-file read limits and binary content checks).

### 1.2 Explicit Workspace Directory Management (`create_directory`)
* **Current Limitation:** Directories are created implicitly as side-effects when creating files, but there is no explicit tool to create empty directory structures.
* **Proposed Enhancement:** Add a `create_directory` tool backed by `WorkspaceSandbox.resolve`, allowing structured directory tree initialization.

### 1.3 Enhanced Git Status & Diff Inspection (`git_diff`)
* **Current Limitation:** Git operations are restricted, but inspecting uncommitted workspace changes cleanly via structured diff summary reduces agent confusion.
* **Proposed Enhancement:** Add structured git status/diff preview tools so the agent can inspect pending changes before proposing commits or resolutions.

---

## 2. Local Semantic Search & Indexing Strategy

### 2.1 Ollama Local Embeddings Engine (`backend/app/indexing/embeddings.py`)
* **Current Limitation:** Semantic search is currently a stub marked as optional.
* **Proposed Enhancement:** Implement local semantic embeddings generation using Ollama's `/api/embeddings` endpoint (e.g., using `nomic-embed-text` or similar local models).
* **Guiding Directives:**
  * Must connect exclusively to the validated loopback Ollama host.
  * Must utilize the shared `OllamaRateLimiter` to prevent GPU/CPU saturation during indexing.
  * Store vector representations in the local SQLite database for fast similarity retrieval.

---

## 3. Frontend UI/UX Improvements

### 3.1 Real-Time Audit Log Search & Filtering
* **Current Limitation:** The frontend audit tab displays up to 80 static entries without query filtering capabilities, despite backend support for `/api/audit?query=...`.
* **Proposed Enhancement:** Add an interactive search input and actor/result filter controls in `HarnessDashboard.tsx` to search audit logs dynamically.

### 3.2 Session Transcript Export
* **Current Limitation:** Session transcripts cannot easily be saved or shared for audit reviews.
* **Proposed Enhancement:** Add "Export Transcript (JSON/Markdown)" buttons to allow operators to download complete session histories with tool calls and approvals.

### 3.3 Enhanced File Browser Navigation
* **Current Limitation:** File browser lists files in a flat list without path search or file type badges.
* **Proposed Enhancement:** Add path filter inputs and improved formatting in the frontend file browser tab.

---

## 4. Safety & Governance Refinements

### 4.1 Granular ReAct Recovery Protocol
* **Current Limitation:** When a non-native tool model returns malformed JSON in ReAct mode, generic error feedback is returned.
* **Proposed Enhancement:** Provide detailed schema hints in ReAct correction messages so smaller models recover instantly without wasting budget iterations.

### 4.2 Automated Pre-change Snapshot Management
* **Current Limitation:** Snapshots in `.harness-snapshots` accumulate indefinitely unless manually removed.
* **Proposed Enhancement:** Implement automated snapshot retention policies (e.g., max age or max total snapshot size) to keep disk usage controlled.

---

## 5. Testing & Quality Assurance

### 5.1 Test Suite Expansion
* Add comprehensive test cases in `backend/tests/` for:
  * `batch_read_files` (valid paths, partial failures, path traversal attempts).
  * `create_directory` (successful creation, sandbox escape prevention, existing path handling).
  * Local embedding generation and vector store operations.
  * Frontend build verification.
