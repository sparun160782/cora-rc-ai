import json
import logging
from typing import Dict, Any, List
from cora_rc_ai.backend_agentic.rag.retrieval.retriever import HybridRetriever

logger = logging.getLogger(__name__)

# Keep a single instance of the retriever
_retriever = None

def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever

def query_regulatory_knowledge_base(query: str) -> str:
    """
    Search the compliance knowledge base for regulatory rules, circulars, clauses, or guidelines.
    Use this tool to find specific clauses (from RBI Master Directions, Basel III, or MiFID II) 
    that apply to a financial transaction or a customer scenario.

    Args:
        query: The search query, regulatory keyword, or compliance question (e.g. 'onboarding KYC requirements').

    Returns:
        A JSON string containing the list of matching sections, clauses, pages, sources, and texts.
    """
    try:
        retriever = get_retriever()
        #result_limit = int(os.getenv("RAG_TOOL_RESULT_LIMIT", "3"))
        #max_chars = int(os.getenv("RAG_TOOL_MAX_CHARS", "900"))
        result_limit = 5
        max_chars = 900
        results = retriever.retrieve(query, limit=result_limit)
        
        formatted_results = []
        for r in results:
            formatted_results.append({
                "document": r["doc_title"],
                "source": r["doc_source"],
                "version": f"v{r['version_number']}",
                "effective_from": str(r["effective_from"]),
                "section": r["section_name"],
                "clause": r["clause_name"],
                "page": r["page_number"],
                "text": (r["chunk_text"] or "")[:max_chars]
            })
            
        return json.dumps(formatted_results, indent=2)
    except Exception as e:
        logger.error(f"Error in query_regulatory_knowledge_base tool: {e}")
        return json.dumps({"error": f"Failed to retrieve data: {str(e)}"})
