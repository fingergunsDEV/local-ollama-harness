from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.db.session_store import SessionStore

SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[=:]\s*[^\s,]+")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if any(word in key.lower() for word in ("secret", "token", "password", "authorization", "api_key")) else redact(item)) for key, item in value.items()}
    if isinstance(value, list): return [redact(item) for item in value]
    if isinstance(value, str): return SECRET_PATTERN.sub("[REDACTED]", value)
    return value


def content_hash(content: str | bytes | None) -> str | None:
    if content is None: return None
    if isinstance(content, str): content = content.encode("utf-8", errors="replace")
    return hashlib.sha256(content).hexdigest()


class AuditLogger:
    """Writes redacted action events to both SQLite and append-only JSONL storage."""

    def __init__(self, store: SessionStore, path: Path) -> None:
        self.store = store
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, *, session_id: str | None, actor: str, action_type: str, tool_name: str | None, target: str | None, result: str, dry_run: bool, approved_by: str = "n/a", params: dict[str, Any] | None = None, content_before: str | bytes | None = None, content_after: str | bytes | None = None) -> dict[str, Any]:
        record = {"timestamp": datetime.now(UTC).isoformat(), "session_id": session_id, "actor": actor, "action_type": action_type, "tool_name": tool_name, "target_path_or_command": target, "params": redact(params or {}), "result": result, "dry_run": dry_run, "approved_by": approved_by, "content_hash_before": content_hash(content_before), "content_hash_after": content_hash(content_after)}
        line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line); handle.flush()
        self.store.add_audit({**record, "target": target})
        return record
