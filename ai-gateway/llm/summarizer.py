from __future__ import annotations

from typing import Any


def compact_messages(messages: list[dict[str, Any]], maximum: int) -> tuple[str | None, list[dict[str, Any]]]:
    """Keep recent context and make a safe, local summary of older plain-text turns."""
    if len(messages) <= maximum:
        return None, messages
    older, recent = messages[:-maximum], messages[-maximum:]
    pieces = [f"{item.get('role', 'user')}: {item.get('content', '')}" for item in older]
    return "Earlier conversation: " + "\n".join(pieces)[-6000:], recent
