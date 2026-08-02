import time
from hashlib import md5


class QueryCache:
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 100):
        self._cache: dict[str, dict] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    def _key(self, query: str) -> str:
        return md5(query.lower().strip().encode()).hexdigest()

    def get(self, query: str) -> dict | None:
        key = self._key(query)
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() - entry["time"] > self._ttl:
            del self._cache[key]
            return None
        return entry["result"]

    def set(self, query: str, result: dict) -> None:
        if len(self._cache) >= self._max_size:
            oldest = min(self._cache, key=lambda k: self._cache[k]["time"])
            del self._cache[oldest]
        self._cache[self._key(query)] = {
            "result": result,
            "time": time.time(),
        }

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)
