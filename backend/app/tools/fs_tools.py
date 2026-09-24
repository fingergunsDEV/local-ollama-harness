from __future__ import annotations

import os
import shutil
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

    def move_file(self, source: str, destination: str, dry_run: bool = True) -> dict[str, Any]:
        src = self.sandbox.resolve(source)
        self.sandbox.ensure_regular_file(src)
        if not src.exists(): raise FileNotFoundError("source file does not exist")
        dst = self.sandbox.resolve(destination)
        self.sandbox.ensure_regular_file(dst)
        plan = f"Move '{self.sandbox.display(src)}' to '{self.sandbox.display(dst)}'"
        if dry_run: return {"applied": False, "dry_run": True, "action": "move", "source": self.sandbox.display(src), "destination": self.sandbox.display(dst), "plan": plan}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
        return {"applied": True, "dry_run": False, "action": "move", "source": self.sandbox.display(src), "destination": self.sandbox.display(dst), "plan": plan}

    def copy_file(self, source: str, destination: str, dry_run: bool = True) -> dict[str, Any]:
        src = self.sandbox.resolve(source)
        self.sandbox.ensure_regular_file(src)
        if not src.exists(): raise FileNotFoundError("source file does not exist")
        dst = self.sandbox.resolve(destination)
        self.sandbox.ensure_regular_file(dst)
        size = src.stat().st_size
        ensure_read_size(size, self.settings)
        ensure_write_size(size, self.settings)
        plan = f"Copy '{self.sandbox.display(src)}' to '{self.sandbox.display(dst)}'"
        if dry_run: return {"applied": False, "dry_run": True, "action": "copy", "source": self.sandbox.display(src), "destination": self.sandbox.display(dst), "plan": plan}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return {"applied": True, "dry_run": False, "action": "copy", "source": self.sandbox.display(src), "destination": self.sandbox.display(dst), "plan": plan}
