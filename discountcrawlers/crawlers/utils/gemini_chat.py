"""discountscraper.utils.gemini_chat
--------------------------------------
Thin wrapper around Gemini Flash chat endpoint.
"""
from __future__ import annotations
import httpx, os, logging, textwrap

_LOGGER = logging.getLogger(__name__)
_KEY = os.getenv("GEMINI_API_KEY")
_CHAT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key=" + _KEY
)

async def chat(prompt: str) -> str:
    payload = {"contents":[{"parts":[{"text":prompt}]}]}
    async with httpx.AsyncClient(http2=True, timeout=45) as cli:
        r = await cli.post(_CHAT, json=payload)
        _LOGGER.info("POST %s → %s", r.url, r.status_code)
        r.raise_for_status()
        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return textwrap.dedent(txt.strip())
