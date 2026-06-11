# Project Name: 👉 CORA – Compliance Oriented Regulatory Assistant
## Tagline: 👉 AI-powered platform for real-time regulatory compliance and transaction screening

# 1. Business Context (Simple Explanation)

**FinServ Global** like a big bank operating in multiple countries (**India, EU, US**).

---

## Problem Statement

### Key Challenges:

- Thousands of rules (laws/regulations) keep changing every year  
- Compliance team manually:
  - Reads long PDF documents  
  - Cross-checks transactions against rules  
  - Prepares audit reports  

👉 This process is **time-consuming (60% effort)** and prone to human error.

---

## Proposed Solution

Build an **AI-powered Compliance Assistant** that:

1. Automatically ingests and understands regulatory documents  
2. Answers natural-language questions (like ChatGPT)  
3. Checks transactions and flags violations  
4. Generates structured compliance reports  

👉 In simple terms:  
**“Google + AI + Rule Engine for Financial Compliance”**

---

# 2. Regulatory Documents Explained

---

## 2.1 Basel III (Bank Safety Rules)

👉 Used globally (especially in US and EU)

### Simple Meaning:

- Banks must maintain **minimum capital (financial buffer)**  
- Ensures they can survive financial stress or crisis  

### Example:

If a bank loans ₹100 crore → it must keep ₹10–15 crore as reserve  

👉 **Why it matters:**
- Prevents bank failures  
- Ensures financial stability  

---

## 2.2 MiFID II (Investor Protection Rules – EU)

👉 Applicable in Europe  

### Simple Meaning:

- Protects customers from risky or unsuitable investments  
- Ensures:
  - Transparency  
  - Fair financial advice  

### Example:

If a customer invests in complex products:

- Bank must check:  
  - ✅ Is the customer knowledgeable?  
  - ✅ Is the product suitable?  

👉 If not → **Violation**

---

## 2.3 RBI Master Directions (India Rules)

👉 Issued by RBI (Reserve Bank of India)

### Simple Meaning:

A **comprehensive rulebook** covering:

- KYC (Know Your Customer)
- Loans and lending
- NBFC operations
- Regulatory reporting

### Example:

- KYC must be verified for all customers  
- Certain lending must support priority sectors (e.g., agriculture)

---

## Summary Table

| Regulation       | Region | Focus                |
|----------------|--------|----------------------|
| Basel III       | Global | Bank stability       |
| MiFID II        | EU     | Investor protection  |
| RBI Directions  | India  | Banking compliance   |

---

# 3. Personas (System Users)

---

## 3.1 Compliance Officer 👨‍💼

### Role:
Day-to-day compliance validation

### Responsibilities:

- Validate whether transactions comply with regulations  
- Ask questions like:
  - *“Is this transaction allowed?”*

### Needs:

- ✅ Fast responses  
- ✅ Clear justification with citations  

---

## 3.2 Compliance Head 👔

### Role:
Oversight and reporting

### Responsibilities:

- Monitor overall compliance posture  
- Generate reports  
- Analyse trends  

### Needs:

- ✅ Consolidated reports  
- ✅ Risk insights and analytics  

---

## 3.3 Internal Auditor 🧾

### Role:
Post-event verification

### Responsibilities:

- Audit past decisions  
- Ask:
  - *“Why was this transaction approved?”*

### Needs:

- ✅ Complete audit trail  
- ✅ Evidence-backed decisions  

---

# 4. Functional Requirements (detailed)

## FR1. Regulatory document ingestion
The platform shall ingest publicly available regulatory content such as Basel III, MiFID II, RBI circulars/master directions, amendments, and supporting policy text. The assignment specifically asks for a multi-format, versioned ingestion strategy and handling of document updates/version control in the vector store. [AI_Archite...Assignment | PDF]
Detailed sub-requirements

Support PDF, HTML, TXT, and structured metadata manifests
Extract document text, headings, tables, footnotes, annexures
Preserve source metadata:

regulation name
document version/effective date
issuing body
jurisdiction
section/clause/page
ingestion timestamp


Maintain version lineage
Detect changed paragraphs/sections on re-ingestion
Mark superseded vs active content
Store canonical source references for citation


## FR2. Natural-language regulatory Q&A
The system must answer regulatory questions like the Basel III example in the assignment and return cited, versioned answers. [AI_Archite...Assignment | PDF]
Detailed sub-requirements

Accept user queries in natural language
Detect regulation/domain intent
Retrieve relevant clauses across multiple regulations
Produce grounded answer with:

concise answer
supporting clauses
source citations
version/effective-date context
confidence score


Refuse or qualify answers when evidence is insufficient
Support follow-up Q&A maintaining session context

## FR3. Transaction screening / compliance assessment

The system must accept a transaction payload and flag applicable regulations, producing a risk-rated compliance assessment. [AI_Archite...Assignment | PDF]
Detailed sub-requirements

Accept structured or semi-structured transaction input:

amount
counterparty
jurisdiction
instrument type
customer type
KYC status
exposure class
product complexity


Run rule + retrieval-assisted analysis
Determine:

applicable regulations
violated/maybe-violated obligations
risk rating
reasoning summary
required remediation steps
evidence and citations


Gracefully handle ambiguity and missing data
Support scenario coverage aligned to the sample transaction payloads listed in the assignment [AI_Archite...Assignment | PDF]


## FR4. Regulatory change impact analysis
When a new circular is ingested, the system must identify which policies, obligations, or transaction types are affected. [AI_Archite...Assignment | PDF]
Detailed sub-requirements

Compare new doc version against previous version
Detect added/removed/amended clauses
Map changed clauses to:

internal policy references
downstream compliance checks
affected transaction categories
impacted dashboards/reports


Generate impact summary with severity classification
Create review tasks for compliance team


## FR5. Report generation
The system must generate a structured compliance report for a set of transactions over a time period. [AI_Archite...Assignment | PDF]
Detailed sub-requirements

Produce weekly/monthly reports
Include:

reporting period
transactions analysed
flagged issues
top regulation categories
risk distribution
unresolved gaps
recommendations
cited examples/evidence


Export to Markdown/PDF/JSON
Produce audit-ready appendix with trace log


## FR6. Audit trail / explainability
The assignment stresses that traceability is non-negotiable and the internal auditor persona needs an audit trail for every AI-assisted decision. [AI_Archite...Assignment | PDF]
Detailed sub-requirements

Log every query, retrieval, rerank, model call, prompt template version, output, citation list, and user action
Persist evidence bundle per decision
Show which document chunks caused the answer
Keep immutable audit records for review
Support replay/debug of historical decisions


## FR7. Evaluation framework
The prototype must include a test dataset with 15–20 Q&A pairs and measure faithfulness, answer relevance, context precision, context recall, using RAGAS or a custom framework. [AI_Archite...Assignment | PDF]

# 6. Non-Functional Requirements (detailed)

The assignment explicitly expects a production-aware architecture, not a tutorial design, and asks for cloud architecture, auto-scaling, observability, security, and cost considerations. [AI_Archite...Assignment | PDF]

## NFR1. Security

Encryption in transit and at rest
Strict role-based access control
No regulated data leakage to external model providers
Masking/redaction of sensitive transaction fields
Auditable admin actions

## NFR2. Compliance / sovereignty

Jurisdiction-aware data residency
Region separation for India/EU/US if expanded beyond prototype
Source/version retention
Evidence retention policy

## NFR3. Performance

Low-latency Q&A for compliance officers
Bounded response times for transaction screening
Asynchronous report generation for heavy workloads

## NFR4. Availability / resilience

Graceful degradation when model/reranker fails
Queue-based ingestion and background processing
Fallback search path if semantic retrieval partially fails

## NFR5. Scalability

Kubernetes-based horizontal scaling
Separate scaling profiles for web/API, retrieval services, and model serving
Concurrency-aware RAG pipeline

## NFR6. Observability

Trace model latency, token usage, cost, retrieval quality, evaluation scores, and drift over time, exactly as the assignment asks. [AI_Archite...Assignment | PDF]

## NFR7. Maintainability

Config-driven architecture
Modular services
Separated orchestration, retrieval, model serving, and UI layers
ADRs for major decisions, as required by the assignment. [AI_Archite...Assignment | PDF]

---

# 7. Cost Estimation (500 concurrent users, 10K queries/day)

This estimate is **indicative** and uses public GCP list prices (us-central1, on-demand, mid-2025). It costs the fully open-source, self-hosted stack described in this document (Ollama + BGE models on GKE, PostgreSQL + pgvector on Cloud SQL) — there is **no per-token LLM vendor charge** because all inference runs in-house (see ADR 2). Cost is therefore dominated by GPU compute amortization.

## 7.1 Load assumptions

| Parameter | Assumption | Notes |
|---|---|---|
| Daily query volume | 10,000 queries/day | ~0.12 QPS average |
| Concurrency | 500 concurrent users | Modeled peak ~16 QPS (1 query / user / ~30s active burst) |
| Tokens per query | ~4,000 input (retrieved context) + ~700 output | Drives GPU throughput sizing |
| Latency SLO | p95 < 3s for Q&A | Requires GPU-backed inference |
| Working hours | Sustained 12h/day peak, scaled-down off-peak | Enables autoscaling savings |

## 7.2 Monthly cost breakdown (indicative)

| Component | Configuration | Qty | Est. $/month |
|---|---|---|---|
| LLM inference (GPU) | GKE node, NVIDIA L4, vLLM serving llama3.1:8b | 2 nodes (1 peak + 1 HA/burst) | ~$1,300 |
| Embedding + reranker (GPU) | Shared L4 node, BGE-large + BGE-reranker | 1 node | ~$650 |
| API + agent pods (CPU) | GKE e2-standard-4, FastAPI + ADK orchestrator | 3 nodes | ~$300 |
| GKE control plane | 1 cluster | 1 | ~$75 |
| Vector DB | Cloud SQL Postgres + pgvector, 4 vCPU / 16 GB, HA | 1 | ~$450 |
| Object storage | GCS, regulatory PDFs + audit artifacts (~100 GB) | — | ~$5 |
| Load balancer + egress | HTTPS LB + moderate egress | — | ~$60 |
| Logging / monitoring | Cloud Logging + Prometheus/Grafana (self-hosted) | — | ~$80 |
| **Total** | | | **~$2,920 / month** |

**Per-query cost:** ~$2,920 / (10,000 × 30) ≈ **$0.0097 per query**.

## 7.3 Cost levers and trade-offs

- **Autoscaling (HPA) to off-peak minimum** — scale GPU nodes down outside business hours; can cut GPU spend 30–40%.
- **Spot/preemptible GPU nodes** for the stateless inference tier — up to ~60% cheaper, with HA replicas on on-demand nodes.
- **Quantized models** (4-bit/8-bit llama3.1:8b) reduce GPU memory, allowing more replicas per node or smaller node types.
- **CPU-only fallback** for embedding/reranking at low traffic — eliminates one GPU node at the cost of latency.
- **Right-sizing context** — trimming retrieved tokens via contextual compression directly lowers GPU throughput needs.

> Trade-off vs. managed APIs: a comparable proprietary-API design (e.g., hosted GPT-4-class model) at this volume would run materially higher per token **and** breach the data-residency/open-source constraints (see ADR 2). Self-hosting trades higher fixed infrastructure cost for predictable spend, full data control, and zero external data egress.

---

