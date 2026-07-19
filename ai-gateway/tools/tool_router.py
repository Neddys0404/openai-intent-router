from __future__ import annotations

from typing import Any
from .docker_tools import docker
from .git_tools import git


class ToolRouter:
    def __init__(self, config: dict[str, Any]):
        self.config = config

    def execute(self, tool: str, command: str) -> dict[str, object]:
        if not self.config.get("enabled", False):
            raise ValueError("Tools are disabled in configuration.")
        if tool == "git":
            return git(command, self.config.get("allowed_git_commands", []))
        if tool == "docker":
            return docker(command, self.config.get("allowed_docker_commands", []))
        raise ValueError(f"Unknown tool '{tool}'.")
