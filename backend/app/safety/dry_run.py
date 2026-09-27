from __future__ import annotations

import difflib
from pathlib import Path


def unified_diff(path: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{path}")) or "(no content change)"


def create_plan(path: Path) -> str:
    return f"Would create regular file: {path}"


def delete_plan(path: Path) -> str:
    return f"Would delete regular file: {path}"


def command_plan(argv: list[str]) -> str:
    return "Would execute argv (without shell): " + repr(argv)
