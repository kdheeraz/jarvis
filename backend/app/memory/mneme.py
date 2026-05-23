"""Long-term memory via Mneme (memory-as-a-service).

Two best-effort calls used by the chat loop:
  recall(query)  -> a short context string of relevant remembered facts (or "")
  remember(text) -> stores a new memory (fire-and-forget)

Both swallow all errors: if Mneme is disabled, unreachable, or slow, the chat
continues unaffected — memory is an enhancement, never a hard dependency.
"""
from __future__ import annotations

import httpx
from loguru import logger

from app.config import get_config


def _cfg():
    return get_config().memory


def _active(text: str = "x") -> bool:
    c = _cfg()
    return bool(c.enabled and c.api_key and (text or "").strip())


def _client(timeout: float = 8.0) -> httpx.Client:
    c = _cfg()
    return httpx.Client(
        base_url=c.base_url.rstrip("/"),
        headers={"X-API-Key": c.api_key},
        timeout=httpx.Timeout(timeout),
    )


def recall(query: str) -> str:
    """Return a compact context block of relevant remembered facts, or "" if none/disabled.
    Safe to call on every turn — blocking, but a local vector search is fast."""
    c = _cfg()
    if not _active(query):
        return ""
    try:
        with _client() as cl:
            r = cl.post(
                "/v1/memories/search",
                json={
                    "query": query,
                    "mode": c.recall_mode,
                    "user_id": c.user_id,
                    "limit": c.recall_limit,
                },
            )
            r.raise_for_status()
            hits = r.json().get("hits", [])
        facts = [h["memory"]["content"] for h in hits if h.get("memory", {}).get("content")]
        if not facts:
            return ""
        bullets = "\n".join(f"- {f}" for f in facts)
        return (
            "Relevant things you remember about this user "
            "(use them if helpful; do not mention that you are recalling memory):\n"
            f"{bullets}"
        )
    except Exception as e:  # never break the chat on a memory hiccup
        logger.warning(f"[mneme] recall failed: {e}")
        return ""


def remember(text: str) -> None:
    """Extract durable facts from the user's message and store them. Fire-and-forget —
    call from a thread, ignore the result. Uses Mneme's /ingest (LLM extraction), so
    greetings and questions are skipped and only real facts are kept. The ingest runs
    an LLM, so it gets a generous timeout (it's off the response path anyway)."""
    c = _cfg()
    if not _active(text):
        return
    try:
        with _client(timeout=60.0) as cl:
            cl.post(
                "/v1/memories/ingest",
                json={
                    "messages": [{"role": "user", "content": text.strip()}],
                    "user_id": c.user_id,
                    "persist": True,
                },
            )
    except Exception as e:
        logger.warning(f"[mneme] remember failed: {e}")
