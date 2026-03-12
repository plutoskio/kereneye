"""Small helpers for file-backed analysis caches."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from services.file_service import write_json_atomic


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
REPORTS_CACHE_DIR = os.path.join(CACHE_DIR, "reports")
NEWS_CACHE_DIR = os.path.join(CACHE_DIR, "news")
BRIEFS_CACHE_DIR = os.path.join(CACHE_DIR, "briefs")


def ensure_cache_dirs() -> None:
    """Create the persistent cache directories used by the API."""
    os.makedirs(REPORTS_CACHE_DIR, exist_ok=True)
    os.makedirs(NEWS_CACHE_DIR, exist_ok=True)
    os.makedirs(BRIEFS_CACHE_DIR, exist_ok=True)


def cache_path(cache_dir: str, key: str) -> str:
    """Build a JSON cache path for a ticker or logical cache key."""
    filename = key if key.endswith(".json") else f"{key}.json"
    return os.path.join(cache_dir, filename)


def load_cached_analysis(cache_file: str, max_age: timedelta) -> tuple[str | None, timedelta | None]:
    """Return cached analysis and its age when the file exists and is still fresh."""
    if not os.path.exists(cache_file):
        return None, None

    try:
        with open(cache_file, "r") as f:
            cached_data = json.load(f)

        timestamp = datetime.fromisoformat(cached_data["timestamp"])
        age = datetime.now() - timestamp
        if age < max_age:
            return cached_data.get("analysis"), age
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None, None

    return None, None


def save_analysis_cache(cache_file: str, analysis: str) -> None:
    """Persist analysis content with a fresh timestamp."""
    write_json_atomic(
        cache_file,
        {
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
        },
    )
