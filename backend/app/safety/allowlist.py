from __future__ import annotations

import re
from pathlib import Path

from app.config import Settings
from app.safety.sandbox import SandboxViolation, WorkspaceSandbox


class CommandDenied(PermissionError):
    """Raised when an agent-proposed command fails the strict command policy."""


SHELL_META = re.compile(r"[;&|`$()<>\n\r]")
GIT_ALLOWED = {"status", "diff", "log", "add", "commit", "branch", "checkout"}
GIT_FORBIDDEN = {"push", "fetch", "pull", "reset", "clean", "rebase", "remote", "config", "-D", "-d"}


class CommandAllowlist:
    """Validates argv before any subprocess is constructed; shell strings are never accepted."""

    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox) -> None:
        self.allowed = settings.allowed_commands
        self.sandbox = sandbox

    def validate(self, argv: list[str]) -> list[str]:
        if not argv or not all(isinstance(value, str) and value for value in argv):
            raise CommandDenied("command must be a non-empty JSON argv list")
        binary = argv[0]
        if Path(binary).name != binary or binary not in self.allowed:
            raise CommandDenied(f"binary is not in EXEC_ALLOWLIST: {binary}")
        if any("\x00" in arg or SHELL_META.search(arg) for arg in argv):
            raise CommandDenied("shell metacharacters, newlines, and null bytes are denied")
        if binary == "git":
            self._validate_git(argv)
        if binary in {"python3", "node", "npm", "pip"}:
            # Interpreters/package managers can escape any argv-only sandbox. A production
            # build may expose them only through an independently verified OS sandbox adapter.
            raise CommandDenied("general-purpose runtime commands are disabled by the safety profile")
        self._validate_path_like_arguments(argv[1:])
        return argv

    def _validate_git(self, argv: list[str]) -> None:
        operation = next((arg for arg in argv[1:] if not arg.startswith("-")), "")
        if operation not in GIT_ALLOWED:
            raise CommandDenied("git operation is not allowed")
        if any(arg in GIT_FORBIDDEN or arg.startswith("--force") for arg in argv[1:]):
            raise CommandDenied("remote, history-destructive, and branch-deletion git operations are denied")
        if operation == "checkout" and any(arg in {"-f", "--force"} for arg in argv):
            raise CommandDenied("forced git checkout is denied")

    def _validate_path_like_arguments(self, args: list[str]) -> None:
        for arg in args:
            if arg.startswith("-"):
                continue
            # Arguments that look like paths must remain sandboxed. Search patterns without
            # separators are harmless data and therefore need no filesystem resolution.
            if "/" in arg or "\\" in arg or arg.startswith("."):
                try:
                    self.sandbox.resolve(arg, allow_root=True)
                except SandboxViolation as exc:
                    raise CommandDenied(str(exc)) from exc
