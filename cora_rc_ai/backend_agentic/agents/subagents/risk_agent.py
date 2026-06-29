"""Transaction compliance risk sub-agent definition."""

from google.adk.agents import LlmAgent

from cora_rc_ai.backend_agentic.agents.dependencies import (
    llm,
    calculate_transaction_risk,
    query_regulatory_knowledge_base,
    generate_and_verify_citation,
)
from cora_rc_ai.backend_agentic.agents.prompts.risk_prompt import RISK_AGENT_PROMPT
from cora_rc_ai.backend_agentic.agents.guardrails import (
    before_model_guardrail,
    after_model_guardrail,
)


risk_agent = LlmAgent(
    name="risk_agent",
    model=llm,
    description=(
        "Evaluates transaction payloads against compliance rules and "
        "returns a structured risk assessment with required actions."
    ),
    instruction=RISK_AGENT_PROMPT,
    tools=[
        calculate_transaction_risk,
        query_regulatory_knowledge_base,
        generate_and_verify_citation,
    ],
    disallow_transfer_to_parent=False,
    before_model_callback=before_model_guardrail,
    after_model_callback=after_model_guardrail,
)
