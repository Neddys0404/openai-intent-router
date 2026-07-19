from __future__ import annotations

from .shell_tools import run_allowed


def git(command: str, allowed: list[str]) -> dict[str, object]:
    if command not in allowed:
        raise ValueError("Git command is not permitted.")
    return run_allowed(["git", command], {"git"})
