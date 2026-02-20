

import os
import re
import math
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Tuple

import httpx

from .selection import select_files, safe_read_text


@dataclass
class Chunk:
    file: str
    text: str


# Simple in-memory embedding cache (per-process)
# key: sha1(model + text) -> vector
_EMBED_CACHE: Dict[str, List[float]] = {}


class RagError(Exception):
    pass


def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "openai").strip().lower()


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(a: List[float]) -> float:
    return math.sqrt(sum(x * x for x in a))


def _cosine(a: List[float], b: List[float]) -> float:
    na = _norm(a)
    nb = _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return _dot(a, b) / (na * nb)


def _openai_embed_cfg() -> Tuple[str, str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RagError("OPENAI_API_KEY environment variable is not set (required for embeddings).")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/").rstrip("/") + "/"
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    return api_key, base_url, model


async def _openai_embeddings(texts: List[str]) -> List[List[float]]:
    api_key, base_url, model = _openai_embed_cfg()
    url = base_url + "embeddings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json={"model": model, "input": texts}, timeout=90.0)

    if r.status_code >= 400:
        raise RagError(f"OpenAI embeddings error ({r.status_code}): {r.text[:500]}")

    data = r.json()
    try:
        # preserve original order
        return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
    except Exception as e:
        raise RagError("Unexpected embeddings response format.") from e


def _keyword_score(query: str, text: str) -> float:
    q = re.findall(r"[A-Za-z_]{3,}", query.lower())
    if not q:
        return 0.0
    t = text.lower()
    hits = sum(1 for w in q if w in t)
    return hits / max(1, len(q))


def chunk_text(file: str, text: str, chunk_chars: int = 2200, overlap: int = 250) -> List[Chunk]:
    chunks: List[Chunk] = []
    s = text.strip()
    if not s:
        return chunks
    i = 0
    n = len(s)
    while i < n:
        j = min(n, i + chunk_chars)
        part = s[i:j]
        chunks.append(Chunk(file=file, text=part))
        if j == n:
            break
        i = max(0, j - overlap)
    return chunks


def build_chunks(repo_root) -> List[Chunk]:
    """Select important files and chunk them."""
    selected = select_files(repo_root, max_files=28)
    all_chunks: List[Chunk] = []
    for sf in selected:
        rel = str(sf.path.relative_to(repo_root))
        txt = safe_read_text(sf.path, max_chars=12000)
        all_chunks.extend(chunk_text(rel, txt))
        if len(all_chunks) > 220:
            break
    return all_chunks[:220]


async def rag_select(chunks: List[Chunk], queries: List[str], top_k: int = 10) -> List[Chunk]:
    """OpenAI: embeddings semantic retrieval; otherwise keyword fallback."""
    provider = _provider()

    if provider == "openai":
        _, _, model = _openai_embed_cfg()

        texts = [c.text for c in chunks]
        keys = [_sha1(model + "\n" + t) for t in texts]
        need_idx = [i for i, k in enumerate(keys) if k not in _EMBED_CACHE]

        if need_idx:
            vecs = await _openai_embeddings([texts[i] for i in need_idx])
            for i, v in zip(need_idx, vecs):
                _EMBED_CACHE[keys[i]] = v

        chunk_vecs = [_EMBED_CACHE[k] for k in keys]
        q_vecs = await _openai_embeddings(queries)

        scored: List[Tuple[float, int]] = []
        for i, cv in enumerate(chunk_vecs):
            best = max(_cosine(cv, qv) for qv in q_vecs)
            scored.append((best, i))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [chunks[i] for _, i in scored[:top_k]]

    scored: List[Tuple[float, int]] = []
    for i, c in enumerate(chunks):
        best = max(_keyword_score(q, c.text) for q in queries)
        scored.append((best, i))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [chunks[i] for _, i in scored[:top_k]]