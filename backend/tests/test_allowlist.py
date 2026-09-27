import pytest

from app.safety.allowlist import CommandAllowlist, CommandDenied


def policy(settings, sandbox): return CommandAllowlist(settings, sandbox)

def test_rejects_shell_injection(settings, sandbox):
    with pytest.raises(CommandDenied): policy(settings, sandbox).validate(["ls", ";id"])
    with pytest.raises(CommandDenied): policy(settings, sandbox).validate(["grep", "$(whoami)"])

def test_rejects_unlisted_and_runtime_binaries(settings, sandbox):
    with pytest.raises(CommandDenied): policy(settings, sandbox).validate(["sh", "-c", "id"])
    with pytest.raises(CommandDenied): policy(settings, sandbox).validate(["python3", "script.py"])

def test_rejects_external_path_smuggling(settings, sandbox):
    with pytest.raises(CommandDenied): policy(settings, sandbox).validate(["cat", "/etc/passwd"])

def test_rejects_git_remote_and_history_destruction(settings, sandbox):
    with pytest.raises(CommandDenied): policy(settings, sandbox).validate(["git", "push"])
    with pytest.raises(CommandDenied): policy(settings, sandbox).validate(["git", "reset", "--hard"])

def test_accepts_safe_read_only_argv(settings, sandbox):
    assert policy(settings, sandbox).validate(["ls", "src"]) == ["ls", "src"]
