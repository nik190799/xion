"""Phase 5h: The Cognition Wiring - Retrieval Engine."""
from .journal import Journal

def retrieve_context(journal: Journal, query: str) -> list[str]:
    """Retrieve relevant context from the journal based on keyword matching."""
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
            
    return unique_results[:5]
