from datetime import datetime, timedelta, timezone
from typing import Any


class CacheService:
    def __init__(self) -> None:
        self._values: dict[str, tuple[Any, datetime | None]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._values.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and expires_at <= datetime.now(timezone.utc):
            self._values.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
        expires_at = None
        if ttl_seconds is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        self._values[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        self._values.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        keys = [key for key in self._values if key.startswith(prefix)]
        for key in keys:
            self._values.pop(key, None)
        return len(keys)

    def status(self) -> str:
        return "ok"


cache = CacheService()
