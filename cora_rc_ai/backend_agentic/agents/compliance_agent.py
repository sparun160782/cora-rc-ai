"""
CORA Compliance Agent - Google ADK powered multi-agent orchestration.
Uses open-source LLM via OpenSourceLlmRouter with RAG, Risk, and Citation tools.
"""
from google.adk.agents import LlmAgent

from cora_rc_ai.backend_agentic.agents.dependencies import (
    llm,
    query_regulatory_knowledge_base,
    calculate_transaction_risk,
    generate_and_verify_citation,
)
from cora_rc_ai.backend_agentic.agents.prompts.root_prompt import ROOT_COMPLIANCE_PROMPT
from cora_rc_ai.backend_agentic.agents.guardrails import (
    before_model_guardrail,
    after_model_guardrail,
)
from cora_rc_ai.backend_agentic.agents.subagents import (
    retrieval_agent,
    risk_agent,
    report_agent,
    change_impact_agent,
)


# Root Agent: Compliance Orchestrator
compliance_agent = LlmAgent(
    name="compliance_agent",
    model=llm,
    description="CORA - AI-powered Compliance Oriented Regulatory Assistant for FinServ Global.",
    instruction=ROOT_COMPLIANCE_PROMPT,
    sub_agents=[retrieval_agent, risk_agent, report_agent, change_impact_agent],
    tools=[
        query_regulatory_knowledge_base,
        calculate_transaction_risk,
        generate_and_verify_citation,
    ],
    before_model_callback=before_model_guardrail,
    after_model_callback=after_model_guardrail,
)


__all__ = ["compliance_agent"]
