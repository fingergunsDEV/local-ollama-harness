from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath

from app.config import Settings


class SandboxViolation(PermissionError):
    """An attempted path escapes or is forbidden within the configured workspace."""


class WorkspaceSandbox:
    """Canonical path guard used by every filesystem, search, git and exec operation."""

    def __init__(self, settings: Settings) -> None:
        self.root = settings.workspace_root.resolve()
        self.follow_symlinks = settings.follow_symlinks
        self.denylist = settings.denylist

    def resolve(self, user_path: str | Path, *, allow_root: bool = False) -> Path:
        raw = str(user_path)
        if "\x00" in raw:
            raise SandboxViolation("null bytes are not valid paths")
        # Treat backslashes as separators so Windows-style traversal cannot bypass checks.
        normalized = raw.replace("\\", "/")
        windows = PureWindowsPath(raw)
        if windows.is_absolute() and not normalized.startswith("/"):
            raise SandboxViolation("Windows absolute paths are not allowed")
        path_obj = Path(normalized)
        if any(part == ".." for part in path_obj.parts):
            raise SandboxViolation("parent traversal segments are denied")

        candidate = path_obj if path_obj.is_absolute() else self.root / path_obj
        try:
            resolved = candidate.resolve(strict=False)
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise SandboxViolation("path is outside WORKSPACE_ROOT") from exc

        if resolved == self.root and not allow_root:
            raise SandboxViolation("workspace root is not a file target")
        relative = resolved.relative_to(self.root).as_posix().lower()
        if self._is_denied(relative):
            raise SandboxViolation("credential-shaped or protected path is denied")

        # resolve(strict=False) follows all existing parents. This explicit check makes
        # the policy auditable and catches a new symlink at any path component.
        current = self.root
        for part in Path(normalized).parts:
            if part in {"", ".", "/"}:
                continue
            current = current / part
            if current.exists() or current.is_symlink():
                if current.is_symlink():
                    target = current.resolve(strict=False)
                    try:
                        target.relative_to(self.root)
                    except ValueError as exc:
                        raise SandboxViolation("symlink target escapes WORKSPACE_ROOT") from exc
                    if not self.follow_symlinks:
                        # Internal symlinks are permitted only because their fully resolved
                        # target is still inside the root. External targets always fail above.
                        continue
        return resolved

    def relative(self, path: Path) -> str:
        return path.resolve(strict=False).relative_to(self.root).as_posix()

    def _is_denied(self, relative: str) -> bool:
        if relative in self.denylist:
            return True
        parts = relative.split("/")
        if any(part.lower() in self.denylist for part in parts):
            return True
        if len(parts) >= 2 and "/".join(parts[-2:]) in self.denylist:
            return True
        return any(part in {".ssh", ".aws", ".gnupg"} for part in parts)

    def ensure_regular_file(self, path: Path) -> None:
        if path.exists() and not path.is_file():
            raise SandboxViolation("target must be a regular file")

    def display(self, path: Path) -> str:
        return os.fspath(path.resolve(strict=False).relative_to(self.root))
