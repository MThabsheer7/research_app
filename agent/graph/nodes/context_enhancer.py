"""
Context Enhancer Node
Receives a single subquestion via Send(), searches with Tavily,
then retrieves top-k chunks using BM25 + cosine similarity (RRF).
"""
import os
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

import numpy as np
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from tavily import TavilyClient
from agent.graph.state import SearchResultModel, FailedTaskModel

load_dotenv()

# ── Clients (module-level, shared across parallel invocations) ───────────────
_tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
_embedder = SentenceTransformer("all-MiniLM-L6-v2")   # 80MB, fast CPU model

TOP_K = 3
RRF_K = 60          # standard RRF constant
CHUNK_TRUNCATE = 250  # max chars per chunk — keeps synthesizer prompt within 4k tokens


# ── RRF helpers ──────────────────────────────────────────────────────────────

def _bm25_ranks(chunks: list[str], query: str) -> list[int]:
    """Return BM25 rank indices (0 = best match)."""
    tokenized = [c.lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.lower().split())
    return list(np.argsort(scores)[::-1])          # descending score → rank order


def _cosine_ranks(chunks: list[str], query: str) -> list[int]:
    """Return cosine similarity rank indices (0 = best match)."""
    texts = [query] + chunks
    embeddings = _embedder.encode(texts, normalize_embeddings=True)
    query_vec = embeddings[0]
    chunk_vecs = embeddings[1:]
    scores = chunk_vecs @ query_vec                # dot product = cosine sim (normalized)
    return list(np.argsort(scores)[::-1])


def _rrf_merge(bm25_order: list[int], cosine_order: list[int], n: int) -> list[int]:
    """
    Reciprocal Rank Fusion: combine two ranked lists into one.
    Returns index order from best to worst (top-n only).
    """
    rrf_scores: dict[int, float] = {}
    for rank, idx in enumerate(bm25_order):
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
    for rank, idx in enumerate(cosine_order):
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
    ranked = sorted(rrf_scores, key=lambda i: rrf_scores[i], reverse=True)
    return ranked[:n]


# ── Node ─────────────────────────────────────────────────────────────────────

def context_enhancer_node(state: dict) -> dict:
    """
    Runs for each subquestion dispatched via Send().
    Returns either:
      - {"search_results": [SearchResultModel]}  on success
      - {"failed_tasks": [FailedTaskModel]}      on failure
    Both fields use operator.add reducers in ResearchState.
    """
    subquestion: str = state["subquestion"]

    try:
        # 1. Search with Tavily
        raw = _tavily.search(
            query=subquestion,
            max_results=5,
            search_depth="advanced",
        )
        results = raw.get("results", [])

        if not results:
            raise ValueError(f"Tavily returned no results for: {subquestion!r}")

        # 2. Extract chunks and their source URLs; truncate to stay within token budget
        chunks: list[str] = [r["content"][:CHUNK_TRUNCATE] for r in results]
        urls: list[str]   = [r["url"]     for r in results]

        # 3. Rank with BM25 + cosine similarity, merge with RRF
        bm25_order   = _bm25_ranks(chunks, subquestion)
        cosine_order = _cosine_ranks(chunks, subquestion)
        top_indices  = _rrf_merge(bm25_order, cosine_order, n=TOP_K)

        # 4. Build SearchResultModel (one per subquestion)
        model = SearchResultModel(
            query=subquestion,
            result=[chunks[i] for i in top_indices],
            source_urls=[urls[i] for i in top_indices],
        )
        return {"search_results": [model]}

    except Exception as e:
        return {
            "failed_tasks": [
                FailedTaskModel(query=subquestion, error=str(e))
            ]
        }