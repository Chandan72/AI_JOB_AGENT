"""
— Simple JSON Cache for Expensive Operations
Caches company research and job extractions for 24 hours.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta


CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_HOURS = 24


def _cache_key(data: str) -> str:
    return hashlib.md5(data.encode()).hexdigest()


def cache_get(key_data: str) -> dict | None:
    key      = _cache_key(key_data)
    cache_file = CACHE_DIR / f"{key}.json"

    if not cache_file.exists():
        return None

    cached = json.loads(cache_file.read_text())
    cached_at = datetime.fromisoformat(cached["cached_at"])

    # Expire after TTL
    if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
        cache_file.unlink()
        return None

    return cached["data"]


def cache_set(key_data: str, data: dict) -> None:
    key       = _cache_key(key_data)
    cache_file = CACHE_DIR / f"{key}.json"
    cache_file.write_text(json.dumps({
        "cached_at": datetime.now().isoformat(),
        "data":      data,
    }))