"""discountscraper.utils.embedding
====================================
Gemini embedding helpers + lightweight RAG support.
"""
from __future__ import annotations

import json, math, os, logging
from pathlib import Path
from typing import List
import httpx

_LOGGER = logging.getLogger(__name__)
_KEY = os.getenv("GEMINI_API_KEY")
if not _KEY:
    raise RuntimeError("Set GEMINI_API_KEY")

_EMB_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-embedding-exp-03-07:embedContent?key=" + _KEY
)

async def embed_text(text: str, task_type: str = "SEMANTIC_SIMILARITY") -> List[float]:
    payload = {
        "model": "models/gemini-embedding-exp-03-07",
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
    }
    async with httpx.AsyncClient(http2=True, timeout=30) as cli:
        r = await cli.post(_EMB_URL, json=payload)
        r.raise_for_status()
        return r.json()["embedding"]["values"]

def save_embedding(vec: List[float], path: str | Path) -> None:
    Path(path).with_suffix(".emb.json").write_text(json.dumps(vec))

def load_embedding(path: str | Path) -> List[float]:
    return json.loads(Path(path).with_suffix(".emb.json").read_text())

def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return dot/(na*nb+1e-9)

async def answer_query(prompt: str, cache_path: str | Path) -> str:
    from .gemini_chat import chat
    cache_path = Path(cache_path)
    deals = json.loads(cache_path.read_text(encoding="utf-8"))
    deals_vec = load_embedding(cache_path)
    prompt_vec = await embed_text(prompt, task_type="QUESTION_ANSWERING")
    if cosine_similarity(prompt_vec, deals_vec) < 0.4:
        return "Ich habe in den gespeicherten Angeboten nichts Passendes gefunden."
    ctx = json.dumps(deals, ensure_ascii=False, indent=2)
    return await chat(f"DEALS_JSON:\n{ctx}\n\nFrage: {prompt}\nAntworte auf Deutsch.")
