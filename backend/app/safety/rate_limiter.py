from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.config import Settings


class RateLimited(RuntimeError):
    pass


@dataclass
class RateStatus:
    tokens_available: float
    max_tokens: int
    in_flight_limit: int
    cooldown_active: bool
    cooldown_remaining_seconds: float
    consecutive_throttles: int


class OllamaRateLimiter:
    """Instance-wide token bucket plus generation concurrency and cooldown state."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.capacity = float(settings.rate_limit_rpm)
        self.tokens = self.capacity
        self.updated_at = time.monotonic()
        self.lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        self.cooldown_until: float | None = None
        self.consecutive_throttles = 0

    async def acquire(self) -> None:
        async with self.lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.updated_at) * self.capacity / 60)
            self.updated_at = now
            if self.cooldown_until and now < self.cooldown_until:
                raise RateLimited(f"cooldown active for {self.cooldown_until - now:.1f} seconds")
            if self.tokens < 1:
                self.consecutive_throttles += 1
                if self.consecutive_throttles >= self.settings.cooldown_trigger_count:
                    self.cooldown_until = now + self.settings.cooldown_seconds
                    self.consecutive_throttles = 0
                    raise RateLimited("rate limit cooldown activated")
                raise RateLimited("token-bucket rate limit reached")
            self.tokens -= 1
            self.consecutive_throttles = 0

    async def generation_slot(self):
        await self.acquire()
        # Acquire before returning the slot so callers cannot start an unbounded number of
        # pending generation requests between constructing and entering context managers.
        await self.semaphore.acquire()
        return _Slot(self.semaphore, acquired=True)

    async def status(self) -> RateStatus:
        async with self.lock:
            now = time.monotonic()
            tokens = min(self.capacity, self.tokens + (now - self.updated_at) * self.capacity / 60)
            remaining = max(0.0, (self.cooldown_until or now) - now)
            if remaining == 0:
                self.cooldown_until = None
            return RateStatus(tokens, int(self.capacity), self.settings.max_concurrent_requests, remaining > 0, remaining, self.consecutive_throttles)


class _Slot:
    def __init__(self, semaphore: asyncio.Semaphore, acquired: bool = False) -> None:
        self.semaphore, self.acquired = semaphore, acquired

    async def __aenter__(self) -> None:
        if not self.acquired:
            await self.semaphore.acquire()
            self.acquired = True

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.acquired:
            self.semaphore.release()
            self.acquired = False
