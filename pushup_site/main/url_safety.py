"""Safe relative redirect targets."""

from __future__ import annotations


def safe_relative_path(path: str | None, default: str = "/") -> str:
    value = (path or "").strip()
    if not value.startswith("/"):
        return default
    if value.startswith("//"):
        return default
    if "://" in value:
        return default
    return value
