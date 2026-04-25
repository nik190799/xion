"""Phase 5h/6.9: Retrieval Engine."""

from __future__ import annotations

from .journal import Journal
from orchestrator.rerank import IdentityReranker, RerankCandidate, Reranker

class JournalIndex:
    """Back-compat index facade for callers importing cognition.journal_index."""

    def __init__(self, journal: Journal):
        self.journal = journal

    def search(self, query: str, *, top_k: int = 5, principal_id: str | None = None) -> list[str]:
        return retrieve_context(self.journal, query, top_k=top_k, principal_id=principal_id)


def retrieve_context(
    journal: Journal,
    query: str,
    *,
    top_k: int = 5,
    search_top_k: int = 20,
    reranker: Reranker | None = None,
    principal_id: str | None = None,
) -> list[str]:
    """Embed -> search top_k=20 -> rerank top_k=5, with keyword fallback."""
    if callable(getattr(journal, "vector_search", None)):
        try:
            raw_hits = journal.vector_search(query, top_k=search_top_k, principal_id=principal_id)
            candidates = [
                RerankCandidate(text=text, score=score, record_id=record_id)
                for text, score, record_id in raw_hits
            ]
            ranker = reranker or IdentityReranker()
            return [hit.text for hit in ranker.rerank(query, candidates, top_k=top_k)]
        except Exception:
            pass

    # Back-compat fallback: keyword matching against the Journal table.
    keywords = [word for word in query.split() if len(word) > 4]
    results = []
    for kw in keywords:
        results.extend(journal.search(kw))
    
    seen = set()
    unique_results = []
    for res in results:
        if res not in seen:
            seen.add(res)
            unique_results.append(res)
            
    return unique_results[:top_k]
