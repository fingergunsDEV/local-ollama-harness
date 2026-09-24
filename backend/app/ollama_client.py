from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import Settings
from app.safety.rate_limiter import OllamaRateLimiter


class OllamaUnavailable(RuntimeError): pass


class OllamaClient:
    """The only network client in the backend; its validated base URL is Ollama-only."""
    def __init__(self, settings: Settings, limiter: OllamaRateLimiter) -> None:
        self.settings, self.limiter = settings, limiter
        self.http = httpx.AsyncClient(base_url=settings.ollama_host.rstrip("/"), timeout=httpx.Timeout(90, connect=5), trust_env=False)

    async def close(self) -> None: await self.http.aclose()

    async def health(self) -> None:
        try:
            response = await self.http.get("/api/tags")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaUnavailable("Ollama is unreachable at configured OLLAMA_HOST") from exc

    async def models(self) -> list[dict[str, Any]]:
        await self.health(); response = await self.http.get("/api/tags")
        return list(response.json().get("models", []))

    async def show(self, model: str) -> dict[str, Any]:
        response = await self.http.post("/api/show", json={"name": model})
        response.raise_for_status(); return response.json()

    async def capabilities(self, model: str) -> dict[str, Any]:
        """Read live model metadata rather than assuming tool-calling support."""
        details = await self.show(model)
        capabilities = {str(item).lower() for item in details.get("capabilities", [])}
        model_info = details.get("model_info", {})
        context_length = next((value for key, value in model_info.items() if "context_length" in key), None)
        return {"native_tools": "tools" in capabilities, "context_length": context_length, "raw": details}

    async def chat(self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> AsyncIterator[dict[str, Any]]:
        payload = {"model": model, "messages": messages, "stream": True, "options": {"num_predict": self.settings.max_output_tokens_per_turn}}
        if tools:
            payload["tools"] = tools
        slot = await self.limiter.generation_slot()
        async with slot:
            try:
                async with self.http.stream("POST", "/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line: continue
                        event = json.loads(line)
                        if event.get("message", {}).get("content"):
                            yield {"type": "token", "content": event["message"]["content"]}
                        if event.get("done"):
                            yield {"type": "complete", "message": event.get("message", {}), "eval_count": int(event.get("eval_count") or 0)}
            except httpx.HTTPError as exc:
                raise OllamaUnavailable("Ollama generation failed") from exc

    async def embed(self, model: str, input_text: str | list[str]) -> list[list[float]]:
        await self.health()
        payload = {"model": model, "input": input_text}
        slot = await self.limiter.generation_slot()
        async with slot:
            try:
                response = await self.http.post("/api/embed", json=payload)
                if response.status_code == 404:
                    prompt = input_text[0] if isinstance(input_text, list) else input_text
                    response = await self.http.post("/api/embeddings", json={"model": model, "prompt": prompt})
                    response.raise_for_status()
                    return [response.json().get("embedding", [])]
                response.raise_for_status()
                data = response.json()
                return data.get("embeddings", [])
            except httpx.HTTPError as exc:
                raise OllamaUnavailable("Ollama embedding generation failed") from exc
