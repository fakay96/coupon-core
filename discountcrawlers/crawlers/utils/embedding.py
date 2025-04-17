"""
discountscraper.utils.embedding
================================
Gemini text–embedding helpers and a tiny RAG layer.

Public API
----------
embed_text(text)           → list[float]
save_embedding(vec, path)  → None
load_embedding(path)       → list[float]
cosine_similarity(a, b)    → float
answer_query(prompt, path) → str
"""
from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
from typing import List

import httpx

LOGGER = logging.getLogger(__name__)
_GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if not _GEMINI_KEY:
    raise RuntimeError("Set GEMINI_API_KEY in the environment")

_EMB_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-embedding-exp-03-07:embedContent"
    f"?key={_GEMINI_KEY}"
)
_HEADERS = {"Content-Type": "application/json"}


async def embed_text(text: str, task_type: str = "SEMANTIC_SIMILARITY") -> List[float]:
    """Return a 4096‑dimensional embedding for *text*."""
    payload = {
        "model": "models/gemini-embedding-exp-03-07",
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
    }
    async with httpx.AsyncClient(http2=True, timeout=30) as cli:
        r = await cli.post(_EMB_URL, headers=_HEADERS, json=payload)
        r.raise_for_status()
        return r.json()["embedding"]["values"]  # type: ignore[index]


def save_embedding(vec: List[float], path: str | Path) -> None:
    Path(path).with_suffix(".emb.json").write_text(json.dumps(vec))


def load_embedding(path: str | Path) -> List[float]:
    return json.loads(Path(path).with_suffix(".emb.json").read_text())


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)


async def answer_query(prompt: str, cache_path: str | Path) -> str:
    """
    Very small Retrieval‑Augmented‑Generation helper.

    * Loads discounts JSON + its embedding (written next to it by the crawler)
    * Embeds the *prompt*
    * If similarity ≥ 0.4, feeds both prompt + JSON into Gemini‑Flash
      and returns the answer in German.
    """
    from .gemini_chat import chat  # local import to avoid circular deps

    cache_path = Path(cache_path)
    deals = json.loads(cache_path.read_text(encoding="utf-8"))
    deals_vec = load_embedding(cache_path)

    prompt_vec = await embed_text(prompt, task_type="QUESTION_ANSWERING")
    sim = cosine_similarity(prompt_vec, deals_vec)
    LOGGER.info("Similarity to deals‑corpus: %.3f", sim)

    if sim < 0.4:
        return "Ich habe in den gespeicherten Angeboten nichts Passendes gefunden."

    ctx = json.dumps(deals, ensure_ascii=False, indent=2)
    return await chat(
        f"Du bist ein Einkaufsassistent.\n\nDEALS_JSON:\n{ctx}\n\nFrage: {prompt}\nAntworte auf Deutsch."
    )
