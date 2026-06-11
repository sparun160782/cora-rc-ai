"""Built-in fallback evaluation dataset.

This mini set is persona-balanced to support quick runs:
- 2 questions for Compliance Officer
- 2 questions for Compliance Head
- 2 questions for Internal Auditor

Keys follow the legacy RAGAS layout (question, answer, contexts, ground_truth)
plus metadata columns.
"""

FALLBACK_TEST_DATA = {
    "question": [
        "For a domestic wire transfer of INR 14 lakh by a newly onboarded customer with incomplete KYC refresh, what compliance checks are mandatory before processing?",
        "Which section of the current RBI KYC direction governs ongoing due diligence for existing customers, and what periodic review obligations apply?",
        "Summarize the top 3 compliance risk themes from this week's flagged transactions and map each theme to governing regulatory clauses.",
        "What operational policy changes are required due to the latest update in customer due diligence, and which teams are impacted?",
        "For transaction ID TXN-2026-00421, provide the full decision trail: retrieved evidence, applied rules, risk score rationale, and final disposition.",
        "Show which regulation version and clause were used for a high-risk decision on 2026-05-18 and provide citation verification status.",
    ],
    "answer": [
        "Mandatory checks include KYC status validation, risk classification, enhanced due diligence trigger assessment, transaction monitoring/escalation, and policy-based hold/review before release.",
        "Ongoing due diligence is governed by the RBI KYC section on monitoring and periodic updation for existing customers, requiring risk-based periodic review and record updates.",
        "Top themes should include suspicious transaction patterns, KYC/documentation gaps, and sanction/PEP screening issues, each mapped to governing RBI/FI compliance clauses.",
        "Required changes should define revised CDD controls, onboarding/monitoring workflow updates, escalation rules, and ownership across compliance, operations, and audit teams.",
        "The decision trail should include retrieved regulatory evidence, rules executed, computed risk rationale, and final approve/hold/reject disposition with timestamps.",
        "The response should show the exact regulation version and clause used, with citation verification status and traceable evidence references.",
    ],
    "contexts": [[""], [""], [""], [""], [""], [""]],
    "ground_truth": [
        "Must mention KYC status validation, enhanced due diligence trigger, transaction monitoring/escalation, and hold/review path based on policy.",
        "Must identify the governing KYC ongoing due diligence section and periodic risk-based review obligations for existing customers.",
        "Must provide three prioritized risk themes and map each to specific regulatory clauses with evidence context.",
        "Must provide concrete policy/process updates and clearly identify impacted teams.",
        "Must provide reproducible end-to-end trace including evidence, applied rules, risk rationale, and final disposition.",
        "Must provide regulation version, clause reference, and citation verification status for auditability.",
    ],
    "persona": [
        "Compliance Officer",
        "Compliance Officer",
        "Compliance Head",
        "Compliance Head",
        "Internal Auditor",
        "Internal Auditor",
    ],
    "category": [
        "Compliance_Officer",
        "Compliance_Officer",
        "Compliance_Head",
        "Compliance_Head",
        "Internal_Auditor",
        "Internal_Auditor",
    ],
    "source_document": [
        "Persona-mini-evalset",
        "Persona-mini-evalset",
        "Persona-mini-evalset",
        "Persona-mini-evalset",
        "Persona-mini-evalset",
        "Persona-mini-evalset",
    ],
}
