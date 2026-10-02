import asyncio

import pytest

from app.safety.rate_limiter import OllamaRateLimiter, RateLimited

@pytest.mark.asyncio
async def test_token_bucket_and_cooldown(settings):
    limiter = OllamaRateLimiter(settings)
    await limiter.acquire(); await limiter.acquire(); await limiter.acquire()
    with pytest.raises(RateLimited): await limiter.acquire()
    with pytest.raises(RateLimited, match="cooldown"): await limiter.acquire()
    status = await limiter.status()
    assert status.cooldown_active
    assert status.cooldown_remaining_seconds > 0

@pytest.mark.asyncio
async def test_concurrency_slot(settings):
    limiter = OllamaRateLimiter(settings)
    slot = await limiter.generation_slot()
    async with slot:
        blocker = asyncio.create_task(limiter.generation_slot())
        await asyncio.sleep(0.02)
        assert not blocker.done()
    acquired = await asyncio.wait_for(blocker, timeout=1)
    async with acquired: pass
