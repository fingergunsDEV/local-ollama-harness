import pytest

from app.safety.allowlist import CommandAllowlist
from app.tools.exec_tools import ExecTools


def test_executes_allowlisted_command_inside_linux_namespaces(settings, sandbox):
    (settings.workspace_root / "visible.txt").write_text("contained\n")
    tool = ExecTools(settings, sandbox, CommandAllowlist(settings, sandbox))
    if not tool.unshare: pytest.skip("Linux unshare namespace adapter unavailable")
    result = tool.execute(["ls"], dry_run=False)
    assert result["sandbox"] == "linux-namespaces"
    assert result["returncode"] == 0, result
    assert "visible.txt" in result["stdout"]

def test_exec_dry_run_never_starts_subprocess(settings, sandbox):
    tool = ExecTools(settings, sandbox, CommandAllowlist(settings, sandbox))
    result = tool.execute(["ls"], dry_run=True)
    assert result["dry_run"] and not result["applied"]
