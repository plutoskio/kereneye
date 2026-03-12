"""Helpers for safe filesystem writes."""

from __future__ import annotations

import json
import os
import tempfile


def write_json_atomic(path: str, payload, *, indent: int | None = None) -> None:
    """Write JSON to a temp file and replace the target atomically."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(
        dir=directory,
        prefix=f".{os.path.basename(path)}.",
        suffix=".tmp",
        text=True,
    )

    try:
        with os.fdopen(fd, "w") as temp_file:
            json.dump(payload, temp_file, indent=indent)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise
