"""Input/output guardrails for CORA ADK agents.

Implements lightweight, dependency-free safety guardrails wired into every
agent through ADK ``before_model_callback`` and ``after_model_callback`` hooks:

* Prompt-injection / jailbreak detection  -> blocks the model call.
* Toxicity / moderation filtering          -> blocks the model call / output.
* PII redaction                            -> masks sensitive data in-place
                                              on both the inbound request and
                                              the outbound model response.

Detection is regex/keyword based so it runs fully offline (no external
moderation API), matching CORA's local-first deployment model. The hooks are
attached to the root agent and all four sub-agents.

Callback contract (ADK):
* ``before_model_callback`` returns ``None`` to continue, or an ``LlmResponse``
  to short-circuit the model call (used to block unsafe input).
* ``after_model_callback`` returns ``None`` to continue, or a modified
  ``LlmResponse`` (used to redact PII / block unsafe output).
"""

import re
import logging
from typing import List, Optional, Tuple

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai.types import Content, Part

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Detection patterns
# --------------------------------------------------------------------------- #

# Prompt-injection / jailbreak attempts.
_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts?|rules)",
        r"disregard\s+(all\s+)?(previous|prior|above|the)\s+(instructions|prompts?|rules)",
        r"forget\s+(everything|all|your)\s+(instructions|rules|above)",
        r"reveal\s+(your\s+)?(system\s+prompt|instructions|hidden\s+prompt)",
        r"(show|print|repeat|output)\s+(me\s+)?(your\s+)?(system\s+prompt|instructions)",
        r"you\s+are\s+now\s+(a|an|in)\b",
        r"\bdeveloper\s+mode\b",
        r"\bdo\s+anything\s+now\b",
        r"\bDAN\b",
        r"\bjailbreak\b",
        r"pretend\s+(you\s+are|to\s+be)\b",
        r"act\s+as\s+(if\s+you\s+are|an?\s+unrestricted)\b",
        r"bypass\s+(your\s+)?(safety|guardrails?|filters?|restrictions?|rules)",
        r"without\s+(any\s+)?(restrictions?|filters?|rules|guardrails?)",
        r"override\s+(your\s+)?(instructions|rules|guardrails?)",
    )
]

# Toxicity / moderation keywords (minimal, conservative list).
_TOXICITY_PATTERNS: List[re.Pattern] = [
    re.compile(rf"\b{p}\b", re.IGNORECASE)
    for p in (
        r"kill\s+(yourself|themselves|him|her|them)",
        r"how\s+to\s+(make|build)\s+(a\s+)?(bomb|explosive|weapon)",
        r"\bgenocide\b",
        r"ethnic\s+cleansing",
    )
]

# PII patterns -> (label, compiled regex). Order matters (more specific first).
_PII_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("AADHAAR", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?\d{1,3}[ -]?)?(?:\(?\d{3,5}\)?[ -]?)\d{3}[ -]?\d{3,4}(?!\d)")),
]

# Message returned to the user when input/output is blocked.
_BLOCK_MESSAGE = (
    "I can't help with that request. CORA is restricted to regulatory "
    "compliance assistance and cannot process instructions that attempt to "
    "bypass its safety rules or that contain unsafe content."
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _redact_pii(text: str) -> Tuple[str, List[str]]:
    """Return ``text`` with PII masked and the list of PII labels found."""
    found: List[str] = []
    redacted = text
    for label, pattern in _PII_PATTERNS:
        if pattern.search(redacted):
            found.append(label)
            redacted = pattern.sub(f"[REDACTED_{label}]", redacted)
    return redacted, found


def _scan_threats(text: str) -> Optional[str]:
    """Return a violation category if ``text`` is unsafe, else ``None``."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return "prompt_injection"
    for pattern in _TOXICITY_PATTERNS:
        if pattern.search(text):
            return "toxicity"
    return None


def _blocking_response(reason: str) -> LlmResponse:
    """Build an LlmResponse that short-circuits the model call."""
    return LlmResponse(
        content=Content(role="model", parts=[Part.from_text(text=_BLOCK_MESSAGE)]),
        turn_complete=True,
        custom_metadata={"guardrail_blocked": True, "guardrail_reason": reason},
    )


def _latest_user_text(llm_request: LlmRequest) -> str:
    """Concatenate text parts from the most recent user turn."""
    for content in reversed(llm_request.contents or []):
        if content.role == "user":
            return "\n".join(p.text for p in (content.parts or []) if getattr(p, "text", None))
    return ""


# --------------------------------------------------------------------------- #
# Callbacks (attached to every agent)
# --------------------------------------------------------------------------- #

def before_model_guardrail(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """Input guardrail: block unsafe input and redact PII before the LLM call."""
    agent_name = getattr(callback_context, "agent_name", "agent")

    # 1) Prompt-injection / jailbreak / toxicity -> block.
    user_text = _latest_user_text(llm_request)
    violation = _scan_threats(user_text)
    if violation:
        logger.warning("[guardrail:%s] blocked input (%s)", agent_name, violation)
        callback_context.state["guardrail_last_block"] = violation
        return _blocking_response(violation)

    # 2) PII redaction -> mask in-place across all user turns, continue.
    redacted_labels: List[str] = []
    for content in llm_request.contents or []:
        if content.role != "user":
            continue
        for part in content.parts or []:
            if getattr(part, "text", None):
                new_text, labels = _redact_pii(part.text)
                if labels:
                    part.text = new_text
                    redacted_labels.extend(labels)
    if redacted_labels:
        logger.info("[guardrail:%s] redacted input PII: %s", agent_name, redacted_labels)
        callback_context.state["guardrail_input_pii"] = sorted(set(redacted_labels))

    return None


def after_model_guardrail(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Output guardrail: block unsafe output and redact PII from the response."""
    agent_name = getattr(callback_context, "agent_name", "agent")

    if not llm_response or not getattr(llm_response, "content", None):
        return None
    parts = getattr(llm_response.content, "parts", None)
    if not parts:
        return None

    output_text = "\n".join(p.text for p in parts if getattr(p, "text", None))
    if not output_text:
        return None

    # 1) Toxic model output -> replace with a safe refusal.
    for pattern in _TOXICITY_PATTERNS:
        if pattern.search(output_text):
            logger.warning("[guardrail:%s] blocked unsafe model output", agent_name)
            callback_context.state["guardrail_last_block"] = "toxic_output"
            return _blocking_response("toxic_output")

    # 2) Redact any PII the model may have echoed back.
    redacted_labels: List[str] = []
    for part in parts:
        if getattr(part, "text", None):
            new_text, labels = _redact_pii(part.text)
            if labels:
                part.text = new_text
                redacted_labels.extend(labels)
    if redacted_labels:
        logger.info("[guardrail:%s] redacted output PII: %s", agent_name, redacted_labels)
        callback_context.state["guardrail_output_pii"] = sorted(set(redacted_labels))
        return llm_response

    return None


__all__ = ["before_model_guardrail", "after_model_guardrail"]
