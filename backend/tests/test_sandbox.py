from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.safety.sandbox import SandboxViolation


def test_denies_parent_traversal(sandbox):
    with pytest.raises(SandboxViolation): sandbox.resolve("../../etc/passwd")

def test_denies_absolute_path_outside_workspace(sandbox):
    with pytest.raises(SandboxViolation): sandbox.resolve("/etc/passwd")

def test_denies_null_bytes_and_windows_absolute_path(sandbox):
    with pytest.raises(SandboxViolation): sandbox.resolve("safe\x00.txt")
    with pytest.raises(SandboxViolation): sandbox.resolve(r"C:\Windows\System32\drivers\etc\hosts")

def test_denies_symlink_escape(settings, sandbox, tmp_path: Path):
    outside = tmp_path / "outside.txt"; outside.write_text("private")
    (settings.workspace_root / "escape").symlink_to(outside)
    with pytest.raises(SandboxViolation): sandbox.resolve("escape")

def test_denies_credential_shaped_files(sandbox):
    with pytest.raises(SandboxViolation): sandbox.resolve(".env")
    with pytest.raises(SandboxViolation): sandbox.resolve("nested/.git/config")
    with pytest.raises(SandboxViolation): sandbox.resolve(".harness-snapshots/backup")

def test_non_loopback_ollama_is_startup_error(tmp_path: Path):
    root = tmp_path / "workspace"; root.mkdir()
    with pytest.raises(ValidationError): Settings(workspace_root=root, ollama_host="http://8.8.8.8:11434")
