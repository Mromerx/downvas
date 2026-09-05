import secrets
import shutil
import time
from typing import Optional

MAX_JOBS = 8
TTL_SECONDS = 30 * 60

_jobs = {}


def _cleanup_entry(entry: Optional[dict]) -> None:
    if not entry:
        return
    try:
        shutil.rmtree(entry["temp_dir"], ignore_errors=True)
    except Exception:
        pass


def _cleanup_expired() -> None:
    now = time.monotonic()
    expired = [k for k, v in _jobs.items() if now - v["created"] > TTL_SECONDS]
    for key in expired:
        _cleanup_entry(_jobs.pop(key, None))


def register_job(path, filename: str, temp_dir, mode: str) -> str:
    """Store a finished download under a single-use token. Returns the token."""
    _cleanup_expired()
    token = secrets.token_urlsafe(24)
    _jobs[token] = {
        "path": str(path),
        "filename": filename,
        "temp_dir": str(temp_dir),
        "mode": mode,
        "created": time.monotonic(),
    }
    if len(_jobs) > MAX_JOBS:
        oldest_key = min(_jobs, key=lambda k: _jobs[k]["created"])
        _cleanup_entry(_jobs.pop(oldest_key, None))
    return token


def take_job(token: str) -> Optional[dict]:
    """Pop and return the job for a token, or None if missing/expired."""
    if not token:
        return None
    _cleanup_expired()
    return _jobs.pop(token, None)