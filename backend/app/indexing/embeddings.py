"""Semantic indexing is intentionally optional and disabled in v1.

When enabled, this module may call only the validated Ollama /api/embeddings endpoint and must
obey the shared OllamaRateLimiter. It must never introduce a cloud embedding provider.
"""
