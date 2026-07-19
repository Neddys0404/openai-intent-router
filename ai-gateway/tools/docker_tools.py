from __future__ import annotations

from .shell_tools import run_allowed


def docker(command: str, allowed: list[str]) -> dict[str, object]:
    if command not in allowed:
        raise ValueError("Docker command is not permitted.")
    return run_allowed(["docker", command], {"docker"})
