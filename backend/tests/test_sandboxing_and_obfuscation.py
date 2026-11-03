import pytest

from app.safety.allowlist import CommandAllowlist, CommandDenied
from app.tools.exec_tools import ExecTools


def test_allowlist_obfuscation_detection(settings, sandbox):
    allowlist = CommandAllowlist(settings, sandbox)

    # Hex escapes
    with pytest.raises(CommandDenied, match="obfuscated"):
        allowlist.validate(["ls", "\\x2fetc"])

    # Octal escapes
    with pytest.raises(CommandDenied, match="obfuscated"):
        allowlist.validate(["cat", "\\057etc\\057passwd"])

    # ANSI-C quoting
    with pytest.raises(CommandDenied, match="obfuscated"):
        allowlist.validate(["grep", "$'pattern'"])

    # Inline base64 decode attempts
    with pytest.raises(CommandDenied, match="obfuscated"):
        allowlist.validate(["cat", "payload | base64 -d"])


def test_exec_tools_adapter_selection_unshare(settings, sandbox):
    allowlist = CommandAllowlist(settings, sandbox)
    settings.exec_sandbox_adapter = "unshare"
    tools = ExecTools(settings, sandbox, allowlist)
    assert tools._resolve_adapter() == "unshare"


def test_exec_tools_adapter_selection_bubblewrap_missing(settings, sandbox, monkeypatch):
    allowlist = CommandAllowlist(settings, sandbox)
    settings.exec_sandbox_adapter = "bubblewrap"
    tools = ExecTools(settings, sandbox, allowlist)
    monkeypatch.setattr(tools, "bwrap", None)

    with pytest.raises(PermissionError, match="required bubblewrap"):
        tools._resolve_adapter()


def test_exec_tools_adapter_selection_auto(settings, sandbox, monkeypatch):
    allowlist = CommandAllowlist(settings, sandbox)
    settings.exec_sandbox_adapter = "auto"
    tools = ExecTools(settings, sandbox, allowlist)

    # When unshare is available, auto chooses unshare
    if tools.unshare:
        assert tools._resolve_adapter() == "unshare"

    # When unshare is unavailable but bwrap is available, auto chooses bubblewrap
    monkeypatch.setattr(tools, "unshare", None)
    monkeypatch.setattr(tools, "bwrap", "/fake/bin/bwrap")
    assert tools._resolve_adapter() == "bubblewrap"

    # When neither is available and exec_require_os_sandbox is True, fails closed
    monkeypatch.setattr(tools, "bwrap", None)
    with pytest.raises(PermissionError, match="fail-closed"):
        tools._resolve_adapter()
