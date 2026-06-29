"""Compliance report generation sub-agent definition."""

from google.adk.agents import LlmAgent

from cora_rc_ai.backend_agentic.agents.dependencies import (
    llm,
    query_regulatory_knowledge_base,
    generate_and_verify_citation,
)
from cora_rc_ai.backend_agentic.agents.prompts.report_prompt import REPORT_AGENT_PROMPT
from cora_rc_ai.backend_agentic.agents.guardrails import (
    before_model_guardrail,
    after_model_guardrail,
)


report_agent = LlmAgent(
    name="report_agent",
    model=llm,
    description="Generates structured weekly/monthly compliance reports in Markdown format.",
    instruction=REPORT_AGENT_PROMPT,
    tools=[
        query_regulatory_knowledge_base,
        generate_and_verify_citation,
    ],
    disallow_transfer_to_parent=False,
    before_model_callback=before_model_guardrail,
    after_model_callback=after_model_guardrail,
)
