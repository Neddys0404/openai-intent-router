from __future__ import annotations

import subprocess


def run_allowed(command: list[str], allowed: set[str], timeout: int = 30) -> dict[str, object]:
    if not command or command[0] not in allowed:
        raise ValueError("Command is not permitted.")
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
