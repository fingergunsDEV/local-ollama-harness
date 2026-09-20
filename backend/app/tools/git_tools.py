from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from app.config import Settings
from app.safety.allowlist import CommandAllowlist
from app.safety.dry_run import command_plan
from app.safety.sandbox import WorkspaceSandbox


class GitTools:
    """Git wrapper with only explicitly named local operations; remote operations never exist here."""
    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, allowlist: CommandAllowlist) -> None:
        self.settings, self.sandbox, self.allowlist = settings, sandbox, allowlist

    def is_repository(self) -> bool:
        return (self.sandbox.root / ".git").exists()

    def execute(self, argv: list[str], dry_run: bool = True) -> dict[str, Any]:
        if not self.is_repository(): raise RuntimeError("WORKSPACE_ROOT is not a git repository")
        validated = self.allowlist.validate(argv)
        action = next((value for value in validated[1:] if not value.startswith("-")), "")
        mutating = action in {"add", "commit", "checkout", "branch"}
        if mutating and dry_run:
            return {"applied": False, "dry_run": True, "action": "git_" + action, "plan": command_plan(validated)}
        if mutating and self.settings.exec_require_os_sandbox:
            # Git checkout/add/commit can invoke hooks or clean/smudge filters defined in an
            # untrusted repository. Do not run them outside a verified OS sandbox.
            raise PermissionError("mutating git operations are fail-closed pending an OS sandbox adapter")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.sandbox.root), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_EXTERNAL_DIFF": "true"}
        completed = subprocess.run(validated, cwd=self.sandbox.root, env=env, text=True, capture_output=True, timeout=30, shell=False, check=False)
        return {"applied": mutating, "dry_run": False, "action": "git_" + action, "argv": validated, "returncode": completed.returncode, "stdout": completed.stdout[-20_000:], "stderr": completed.stderr[-10_000:]}
