"""Shared utilities for message/content extraction."""
from typing import Any, List


def extract_message_content(msg: Any) -> str:
    """Extract text content from a message (dict or object). Handles str and list content."""
    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return str(content)


def last_ai_content(messages: List[Any]) -> str:
    """Return the text content of the last AI message in the list."""
    for msg in reversed(messages):
        role = getattr(msg, "type", None) or (
            msg.get("type") if isinstance(msg, dict) else msg.get("role")
        )
        if role in ("ai", "assistant"):
            return extract_message_content(msg) or ""
    return ""
