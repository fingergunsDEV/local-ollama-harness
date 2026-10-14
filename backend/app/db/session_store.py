from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, created_at TEXT NOT NULL, model TEXT NOT NULL, dry_run INTEGER NOT NULL,
  workspace_root TEXT NOT NULL, status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
  token_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);
CREATE TABLE IF NOT EXISTS tool_calls (
  id TEXT PRIMARY KEY, session_id TEXT NOT NULL, message_id TEXT, tool_name TEXT NOT NULL,
  params_json TEXT NOT NULL, result_json TEXT, status TEXT NOT NULL, dry_run INTEGER NOT NULL,
  created_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES sessions(id)
);
CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY, session_id TEXT NOT NULL, tool_call_id TEXT NOT NULL, action_type TEXT NOT NULL,
  diff_or_plan TEXT NOT NULL, status TEXT NOT NULL, resolved_by TEXT, resolved_at TEXT,
  FOREIGN KEY(session_id) REFERENCES sessions(id), FOREIGN KEY(tool_call_id) REFERENCES tool_calls(id)
);
CREATE TABLE IF NOT EXISTS audit_log (
  id TEXT PRIMARY KEY, session_id TEXT, actor TEXT NOT NULL, action_type TEXT NOT NULL,
  tool_name TEXT, target TEXT, result TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS file_index (
  path TEXT PRIMARY KEY, hash TEXT NOT NULL, size INTEGER NOT NULL, mtime REAL NOT NULL, indexed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_approvals_session ON approvals(session_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id, created_at);
"""


def now() -> str:
    return datetime.now(UTC).isoformat()


class SessionStore:
    """Small, parameterized SQLite data layer. All state-changing operations are transactional."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(query, params)

    def create_session(self, model: str, dry_run: bool, workspace_root: str) -> dict[str, Any]:
        record = {"id": str(uuid.uuid4()), "created_at": now(), "model": model, "dry_run": int(dry_run), "workspace_root": workspace_root, "status": "idle"}
        self._execute("INSERT INTO sessions(id, created_at, model, dry_run, workspace_root, status) VALUES(:id,:created_at,:model,:dry_run,:workspace_root,:status)", record)
        record["dry_run"] = bool(record["dry_run"])
        return record

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return self._row(row)

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC LIMIT 100").fetchall()
        return [self._row(row) for row in rows]

    def set_session_status(self, session_id: str, status: str) -> None:
        self._execute("UPDATE sessions SET status=? WHERE id=?", (status, session_id))

    def set_dry_run(self, session_id: str, value: bool) -> None:
        self._execute("UPDATE sessions SET dry_run=? WHERE id=?", (int(value), session_id))

    def add_message(self, session_id: str, role: str, content: str, token_count: int = 0) -> str:
        message_id = str(uuid.uuid4())
        self._execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (message_id, session_id, role, content, token_count, now()))
        return message_id

    def messages(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT * FROM messages WHERE session_id=? ORDER BY created_at", (session_id,)).fetchall()
        return [self._row(row) for row in rows]

    def start_tool_call(self, session_id: str, message_id: str | None, name: str, params: dict[str, Any], dry_run: bool) -> str:
        tool_call_id = str(uuid.uuid4())
        self._execute("INSERT INTO tool_calls VALUES(?,?,?,?,?,?,?,?,?)", (tool_call_id, session_id, message_id, name, json.dumps(params, sort_keys=True), None, "started", int(dry_run), now()))
        return tool_call_id

    def finish_tool_call(self, tool_call_id: str, result: dict[str, Any], status: str) -> None:
        self._execute("UPDATE tool_calls SET result_json=?, status=? WHERE id=?", (json.dumps(result, sort_keys=True), status, tool_call_id))

    def create_approval(self, session_id: str, tool_call_id: str, action_type: str, diff_or_plan: str) -> str:
        approval_id = str(uuid.uuid4())
        self._execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?)", (approval_id, session_id, tool_call_id, action_type, diff_or_plan, "pending", None, None))
        return approval_id

    def resolve_approval(self, approval_id: str, status: str, resolved_by: str) -> None:
        self._execute("UPDATE approvals SET status=?, resolved_by=?, resolved_at=? WHERE id=? AND status='pending'", (status, resolved_by, now(), approval_id))

    def approval_status(self, approval_id: str) -> str:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT status FROM approvals WHERE id=?", (approval_id,)).fetchone()
        return str(row["status"]) if row else "missing"

    def pending_approvals(self, session_id: str | None = None) -> list[dict[str, Any]]:
        query, values = ("SELECT * FROM approvals WHERE status='pending' ORDER BY rowid DESC", ()) if session_id is None else ("SELECT * FROM approvals WHERE session_id=? AND status='pending' ORDER BY rowid DESC", (session_id,))
        with self._lock, self._connect() as conn:
            rows = conn.execute(query, values).fetchall()
        return [self._row(row) for row in rows]

    def fork_session(self, parent_session_id: str, up_to_message_id: str | None = None) -> dict[str, Any]:
        parent = self.get_session(parent_session_id)
        if not parent:
            raise ValueError(f"Parent session '{parent_session_id}' not found")

        new_session = self.create_session(
            model=parent["model"],
            dry_run=parent["dry_run"],
            workspace_root=parent["workspace_root"],
        )

        parent_messages = self.messages(parent_session_id)
        messages_to_copy = []
        for msg in parent_messages:
            messages_to_copy.append(msg)
            if up_to_message_id and msg["id"] == up_to_message_id:
                break

        with self._lock, self._connect() as conn:
            for msg in messages_to_copy:
                conn.execute(
                    "INSERT INTO messages VALUES(?,?,?,?,?,?)",
                    (str(uuid.uuid4()), new_session["id"], msg["role"], msg["content"], msg["token_count"], msg["created_at"]),
                )

        return new_session

    def export_session(self, session_id: str, format_type: str = "markdown") -> str | dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found")

        msgs = self.messages(session_id)
        with self._lock, self._connect() as conn:
            tool_rows = conn.execute("SELECT * FROM tool_calls WHERE session_id=? ORDER BY created_at", (session_id,)).fetchall()
            tool_calls = [self._row(r) for r in tool_rows]

        if format_type.lower() == "json":
            return {
                "session": session,
                "messages": msgs,
                "tool_calls": tool_calls,
            }

        # Default: Markdown
        lines = [
            f"# Session Export: {session['id']}",
            f"- **Model:** {session['model']}",
            f"- **Created At:** {session['created_at']}",
            f"- **Dry Run:** {session['dry_run']}",
            f"- **Workspace Root:** {session['workspace_root']}",
            f"- **Status:** {session['status']}",
            "",
            "## Conversation Transcript",
            "",
        ]

        for msg in msgs:
            role = msg["role"].upper()
            created = msg["created_at"]
            lines.append(f"### {role} ({created})")
            lines.append(msg["content"])
            lines.append("")

        if tool_calls:
            lines.append("## Executed Tool Calls")
            lines.append("")
            for tc in tool_calls:
                lines.append(f"- **{tc['tool_name']}** (status: {tc['status']}, dry_run: {tc['dry_run']})")
                if tc.get("params_json"):
                    lines.append(f"  - Params: `{json.dumps(tc['params_json'])}`")
                if tc.get("result_json"):
                    lines.append(f"  - Result: `{json.dumps(tc['result_json'])}`")

        return "\n".join(lines)

    def add_audit(self, record: dict[str, Any]) -> None:
        self._execute("INSERT INTO audit_log VALUES(?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), record.get("session_id"), record["actor"], record["action_type"], record.get("tool_name"), record.get("target"), record["result"], json.dumps(record, sort_keys=True), record["timestamp"]))

    def audit_entries(
        self,
        session_id: str | None = None,
        query: str = "",
        action_type: str | None = None,
        result: str | None = None,
        tool_name: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        values: list[Any] = []

        if session_id:
            conditions.append("session_id = ?")
            values.append(session_id)
        if query:
            conditions.append("(target LIKE ? OR action_type LIKE ? OR result LIKE ?)")
            values.extend([f"%{query}%"] * 3)
        if action_type:
            conditions.append("action_type = ?")
            values.append(action_type)
        if result:
            conditions.append("result = ?")
            values.append(result)
        if tool_name:
            conditions.append("tool_name = ?")
            values.append(tool_name)
        if date_from:
            conditions.append("created_at >= ?")
            values.append(date_from)
        if date_to:
            conditions.append("created_at <= ?")
            values.append(date_to)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"SELECT * FROM audit_log{where_clause} ORDER BY created_at DESC LIMIT ?"
        values.append(limit)

        with self._lock, self._connect() as conn:
            rows = conn.execute(sql, values).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None: return None
        data = dict(row)
        if "dry_run" in data: data["dry_run"] = bool(data["dry_run"])
        for name in ("params_json", "result_json", "payload_json"):
            if data.get(name): data[name] = json.loads(data[name])
        return data
