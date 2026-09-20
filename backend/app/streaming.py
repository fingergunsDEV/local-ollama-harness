from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any


def encode_sse(event: dict[str, Any]) -> bytes:
    event_type = str(event.get("type", "message"))
    return f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")


async def sse_events(events: AsyncIterator[dict[str, Any]]) -> AsyncIterator[bytes]:
    async for event in events:
        yield encode_sse(event)
