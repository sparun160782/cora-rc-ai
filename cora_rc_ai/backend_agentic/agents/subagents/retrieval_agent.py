"""Regulatory retrieval sub-agent definition."""

from google.adk.agents import LlmAgent

from cora_rc_ai.backend_agentic.agents.dependencies import (
    llm,
    query_regulatory_knowledge_base,
    generate_and_verify_citation,
)
from cora_rc_ai.backend_agentic.agents.prompts.retrieval_prompt import RETRIEVAL_AGENT_PROMPT
from cora_rc_ai.backend_agentic.agents.guardrails import (
    before_model_guardrail,
    after_model_guardrail,
)


retrieval_agent = LlmAgent(
    name="retrieval_agent",
    model=llm,
    description=(
        "Answers natural-language regulatory questions by retrieving relevant "
        "clauses from RBI, Basel III, MiFID II, FATF, and other regulations."
    ),
    instruction=RETRIEVAL_AGENT_PROMPT,
    tools=[
        query_regulatory_knowledge_base,
        generate_and_verify_citation,
    ],
    disallow_transfer_to_parent=False,
    before_model_callback=before_model_guardrail,
    after_model_callback=after_model_guardrail,
)
