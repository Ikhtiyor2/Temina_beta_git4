"""Server-side rep validation — caps client-submitted counts."""

from __future__ import annotations

from typing import Any

MAX_CLIENT_REPS_PER_SESSION = 500
MAX_REPS_PER_MINUTE = 45


def sanitize_client_reps(
    reps: int,
    *,
    server_count: int | None = None,
    integrity: dict[str, Any] | None = None,
) -> int:
    """Return a trusted rep count capped against server state and integrity signals."""
    reps = max(0, int(reps or 0))

    if server_count is not None and server_count >= 0:
        reps = min(reps, int(server_count))

    if not isinstance(integrity, dict) or not integrity:
        return min(reps, MAX_CLIENT_REPS_PER_SESSION)

    tracked = int(integrity.get("tracked_reps") or 0)
    client = int(integrity.get("client_reps") or reps)
    valid_ratio = float(integrity.get("valid_pose_ratio") or 1.0)
    max_rpm = int(integrity.get("max_reps_per_minute") or 0)
    flags = integrity.get("flags") or []

    if tracked > 0 and client > tracked and client - tracked > max(1, tracked * 0.1):
        reps = min(reps, tracked)
    if max_rpm > MAX_REPS_PER_MINUTE:
        reps = min(reps, MAX_REPS_PER_MINUTE)
    if valid_ratio < 0.5:
        reps = int(reps * max(valid_ratio, 0.25))
    if "REP_RATE_EXCEEDED" in flags:
        reps = min(reps, MAX_REPS_PER_MINUTE)
    if "LOW_TRACKED_RATIO" in flags and tracked > 0:
        reps = min(reps, tracked)

    return min(max(0, reps), MAX_CLIENT_REPS_PER_SESSION)
