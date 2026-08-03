import asyncio
import time
from loguru import logger


class AsyncRateLimiter:
    """Sliding-window rate limiter shared across all Gemini callers.

    Ensures we never send more than max_requests within period_seconds,
    which prevents 429 (RESOURCE_EXHAUSTED) errors that cause 30s+ retries.
    """

    def __init__(self, max_requests: int, period_seconds: float = 60.0):
        self.max_requests = max_requests
        self.period_seconds = period_seconds
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        waited = 0.0
        async with self._lock:
            now = time.monotonic()
            self._timestamps = [t for t in self._timestamps if now - t < self.period_seconds]
            if len(self._timestamps) >= self.max_requests:
                wait = self._timestamps[0] + self.period_seconds - now
                if wait > 0:
                    logger.info(f"[RateLimiter] {self.max_requests} req/min reached, waiting {wait:.1f}s")
                    waited = wait
                    await asyncio.sleep(wait)
                    now = time.monotonic()
                    self._timestamps = [t for t in self._timestamps if now - t < self.period_seconds]
            self._timestamps.append(now)
        return waited

    def pending(self) -> int:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < self.period_seconds]
        return len(self._timestamps)


gemini_rate_limiter = AsyncRateLimiter(max_requests=15, period_seconds=60.0)
