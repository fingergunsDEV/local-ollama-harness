from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.config import Settings
from app.safety.allowlist import CommandAllowlist
from app.safety.dry_run import command_plan
from app.safety.sandbox import WorkspaceSandbox


class ExecTools:
    """Run an allowlisted argv inside a local Linux user/mount/network/PID namespace.

    The caller-controlled command is always an argv tail. The fixed shell program below belongs to
    the sandbox adapter, not the agent: it only creates mounts, chroots, and executes that argv.
    No agent strings are interpolated into the adapter program.
    """

    _NAMESPACE_SETUP = r'''
mount --make-rprivate /
root="$HARNESS_SANDBOX_ROOT"
mount -t tmpfs -o mode=755,nosuid,nodev tmpfs "$root"
mkdir -p "$root"/workspace "$root"/usr "$root"/proc "$root"/tmp
# The only project data mount is the configured workspace. It is writable only because an
# approval-gated, non-dry-run exec can legitimately produce workspace artifacts.
mount --bind "$HARNESS_WORKSPACE_ROOT" "$root/workspace"
mount -o remount,bind,nosuid,nodev "$root/workspace"
# Runtime binaries/libraries are visible read-only; no host configuration or home directory is mounted.
mount --bind /usr "$root/usr"
mount -o remount,bind,ro,nosuid,nodev "$root/usr"
(cd "$root"; ln -s usr/bin bin; ln -s usr/lib lib; ln -s usr/lib64 lib64; ln -s usr/sbin sbin)
mount -t proc -o nosuid,nodev,noexec proc "$root/proc"
# chroot can reset the current directory, so a second fixed launcher enters the only writable
# project mount before forwarding the validated argv as positional parameters.
exec /usr/sbin/chroot "$root" /usr/bin/env -i PATH=/usr/bin:/bin HOME=/workspace LANG=C.UTF-8 LC_ALL=C.UTF-8 /usr/bin/sh -ceu 'cd /workspace; exec "$@"' _ "$@"
'''

    def __init__(self, settings: Settings, sandbox: WorkspaceSandbox, allowlist: CommandAllowlist) -> None:
        self.settings, self.sandbox, self.allowlist = settings, sandbox, allowlist
        self.unshare = shutil.which("unshare")

    def execute(self, argv: list[str], dry_run: bool = True) -> dict[str, Any]:
        validated = self.allowlist.validate(argv)
        if dry_run:
            return {"applied": False, "dry_run": True, "action": "exec", "plan": command_plan(validated)}
        if self.settings.exec_require_os_sandbox and not self.unshare:
            raise PermissionError("exec is fail-closed: required Linux unshare sandbox adapter is unavailable")
        if not self.unshare:
            raise PermissionError("exec requires the Linux unshare sandbox adapter")
        return self._run_in_namespace(validated)

    def _run_in_namespace(self, argv: list[str]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="ollama-harness-exec-") as temp_root:
            env = {
                "PATH": "/usr/bin:/bin",
                "HARNESS_SANDBOX_ROOT": temp_root,
                "HARNESS_WORKSPACE_ROOT": str(self.sandbox.root),
            }
            # User, mount, network and PID namespaces are all created before the setup program.
            # The network namespace has no configured interface, so no outbound route exists.
            command = [self.unshare, "--user", "--map-root-user", "--mount", "--net", "--pid", "--fork", "--mount-proc", "sh", "-ceu", self._NAMESPACE_SETUP, "_", *argv]
            process = subprocess.Popen(command, cwd=self.sandbox.root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True, shell=False)
            try:
                stdout, stderr = process.communicate(timeout=self.settings.exec_timeout_seconds)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
                return {"applied": True, "dry_run": False, "action": "exec", "argv": argv, "returncode": None, "timed_out": True, "sandbox": "linux-namespaces", "stdout": stdout[-20_000:], "stderr": stderr[-10_000:]}
            return {"applied": True, "dry_run": False, "action": "exec", "argv": argv, "returncode": process.returncode, "timed_out": False, "sandbox": "linux-namespaces", "stdout": stdout[-20_000:], "stderr": stderr[-10_000:]}
