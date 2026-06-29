"""Prompt constants for CORA compliance agents."""

from cora_rc_ai.backend_agentic.agents.prompts.retrieval_prompt import RETRIEVAL_AGENT_PROMPT
from cora_rc_ai.backend_agentic.agents.prompts.risk_prompt import RISK_AGENT_PROMPT
from cora_rc_ai.backend_agentic.agents.prompts.change_impact_prompt import CHANGE_IMPACT_AGENT_PROMPT
from cora_rc_ai.backend_agentic.agents.prompts.report_prompt import REPORT_AGENT_PROMPT
from cora_rc_ai.backend_agentic.agents.prompts.root_prompt import ROOT_COMPLIANCE_PROMPT


__all__ = [
    "RETRIEVAL_AGENT_PROMPT",
    "RISK_AGENT_PROMPT",
    "CHANGE_IMPACT_AGENT_PROMPT",
    "REPORT_AGENT_PROMPT",
    "ROOT_COMPLIANCE_PROMPT",
]
