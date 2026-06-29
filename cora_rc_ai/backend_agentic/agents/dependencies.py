"""Shared dependencies for CORA agent modules."""

from cora_rc_ai.backend_agentic.models.llm_router import OpenSourceLlmRouter
from cora_rc_ai.backend_agentic.tools.rag_tool import query_regulatory_knowledge_base
from cora_rc_ai.backend_agentic.tools.risk_calculator import calculate_transaction_risk
from cora_rc_ai.backend_agentic.tools.citation_tool import generate_and_verify_citation


# Shared open-source LLM instance (Ollama/vLLM)
llm = OpenSourceLlmRouter()


__all__ = [
    "llm",
    "query_regulatory_knowledge_base",
    "calculate_transaction_risk",
    "generate_and_verify_citation",
]
