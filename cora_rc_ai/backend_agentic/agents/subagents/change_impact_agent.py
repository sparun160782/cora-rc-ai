"""Regulatory change impact sub-agent definition."""

from google.adk.agents import LlmAgent

from cora_rc_ai.backend_agentic.agents.dependencies import (
    llm,
    query_regulatory_knowledge_base,
    generate_and_verify_citation,
)
from cora_rc_ai.backend_agentic.agents.prompts.change_impact_prompt import CHANGE_IMPACT_AGENT_PROMPT
from cora_rc_ai.backend_agentic.agents.guardrails import (
    before_model_guardrail,
    after_model_guardrail,
)


change_impact_agent = LlmAgent(
    name="change_impact_agent",
    model=llm,
    description=(
        "Analyzes newly ingested circulars, amendments, or regulation changes "
        "to evaluate their impact on existing bank policies, derivative rules, or NBFC frameworks."
    ),
    instruction=CHANGE_IMPACT_AGENT_PROMPT,
    tools=[
        query_regulatory_knowledge_base,
        generate_and_verify_citation,
    ],
    disallow_transfer_to_parent=False,
    before_model_callback=before_model_guardrail,
    after_model_callback=after_model_guardrail,
)
