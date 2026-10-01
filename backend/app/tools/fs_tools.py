from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.config import Settings
from app.safety.dry_run import create_plan, delete_plan, unified_diff
from app.safety.limits import LimitExceeded, ensure_read_size, ensure_write_size
from app.safety.sandbox import WorkspaceSandbox


class FileTools:
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox) -> None:
        self.settings, self.sandbox = settings, sandbox

    def read_file(self, path: str, offset: int = 0, length: int | None = None) -> dict[str, Any]:
        target = self.sandbox.resolve(path)
        self.sandbox.ensure_regular_file(target)
        size = target.stat().st_size
        ensure_read_size(size if length is None else min(size, length), self.settings)
        if offset < 0 or (length is not None and length < 0): raise ValueError("offset and length must be non-negative")
        with target.open("rb") as handle:
            handle.seek(offset); raw = handle.read(length)
        if b"\x00" in raw[:8192]: raise ValueError("binary content cannot be read as text")
        return {"path": self.sandbox.display(target), "content": raw.decode("utf-8", errors="replace"), "size": size, "offset": offset, "truncated": offset + len(raw) < size}

    def list_files(self, path: str = ".", depth: int = 3) -> dict[str, Any]:
        root = self.sandbox.resolve(path, allow_root=True)
        if depth < 0 or depth > 10: raise ValueError("depth must be between 0 and 10")
        entries: list[dict[str, Any]] = []
        for candidate in sorted(root.rglob("*")):
            try: relative = candidate.relative_to(root)
            except ValueError: continue
            if len(relative.parts) > depth: continue
            try: resolved = self.sandbox.resolve(candidate)
            except (PermissionError, ValueError): continue
            entries.append({"path": self.sandbox.display(resolved), "type": "dir" if resolved.is_dir() else "file", "size": resolved.stat().st_size if resolved.is_file() else None})
            if len(entries) >= self.settings.max_files_indexed: break
        return {"path": self.sandbox.display(root) if root != self.sandbox.root else ".", "entries": entries, "truncated": len(entries) >= self.settings.max_files_indexed}

    def stat_file(self, path: str) -> dict[str, Any]:
        target = self.sandbox.resolve(path)
        status = target.stat()
        return {"path": self.sandbox.display(target), "size": status.st_size, "mtime": status.st_mtime, "is_file": target.is_file(), "is_dir": target.is_dir()}

    def write_file(self, path: str, content: str, dry_run: bool = True) -> dict[str, Any]:
        target = self.sandbox.resolve(path); self.sandbox.ensure_regular_file(target)
        raw = content.encode("utf-8"); ensure_write_size(len(raw), self.settings)
        before = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        diff = unified_diff(self.sandbox.display(target), before, content)
        if dry_run: return {"applied": False, "dry_run": True, "action": "write", "path": self.sandbox.display(target), "diff": diff}
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        return {"applied": True, "dry_run": False, "action": "write", "path": self.sandbox.display(target), "diff": diff}

    def create_file(self, path: str, content: str = "", dry_run: bool = True) -> dict[str, Any]:
        target = self.sandbox.resolve(path)
        if target.exists(): raise FileExistsError("file already exists; use write_file")
        ensure_write_size(len(content.encode("utf-8")), self.settings)
        plan = create_plan(target)
        if dry_run: return {"applied": False, "dry_run": True, "action": "create", "path": self.sandbox.display(target), "plan": plan}
        target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content, encoding="utf-8")
        return {"applied": True, "dry_run": False, "action": "create", "path": self.sandbox.display(target), "plan": plan}

    def delete_file(self, path: str, dry_run: bool = True) -> dict[str, Any]:
        target = self.sandbox.resolve(path); self.sandbox.ensure_regular_file(target)
        if not target.exists(): raise FileNotFoundError("cannot delete missing file")
        plan = delete_plan(target)
        if dry_run: return {"applied": False, "dry_run": True, "action": "delete", "path": self.sandbox.display(target), "plan": plan}
        target.unlink()
        return {"applied": True, "dry_run": False, "action": "delete", "path": self.sandbox.display(target), "plan": plan}

    def workspace_summary(self, path: str = ".") -> dict[str, Any]:
        root = self.sandbox.resolve(path, allow_root=True)
        file_counts: dict[str, int] = {}
        total_files = 0
        total_directories = 0
        total_lines = 0

        for candidate in root.rglob("*"):
            try:
                resolved = self.sandbox.resolve(candidate)
            except (PermissionError, ValueError, OSError):
                continue

            if resolved.is_dir():
                total_directories += 1
                continue

            if resolved.is_file():
                total_files += 1
                ext = resolved.suffix.lower() or "no_extension"
                file_counts[ext] = file_counts.get(ext, 0) + 1

                if resolved.stat().st_size <= self.settings.max_file_read_bytes:
                    try:
                        raw = resolved.read_bytes()
                        if b"\x00" not in raw[:8192]:
                            total_lines += raw.count(b"\n") + (1 if raw else 0)
                    except OSError:
                        pass

        return {
            "root": self.sandbox.display(root) if root != self.sandbox.root else ".",
            "total_files": total_files,
            "total_directories": total_directories,
            "total_lines": total_lines,
            "file_counts_by_extension": file_counts,
        }
