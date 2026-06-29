# AI-Powered Regulatory Compliance Assistant

## Solution Architecture & Design

### Author

Arun S. P.

---

# 1. Executive Summary

The objective is to design and implement an AI-powered Regulatory Compliance Assistant capable of:

* Ingesting regulatory documents such as RBI circulars, Basel III guidelines, regulatory amendments, and policy documents.
* Supporting Retrieval Augmented Generation (RAG) for accurate regulation lookup.
* Providing source-attributed and explainable answers.
* Performing compliance assessments on financial transactions.
* Operating through an Agentic framework using Google Agent Development Kit (ADK).
* Supporting auditability, document versioning, and regulatory traceability.

The proposed architecture leverages:

* Google ADK for Agentic orchestration
* FastAPI for backend services
* PostgreSQL + pgvector as the vector database
* Hybrid Retrieval (BM25 + Vector Search)
* BGE Embeddings and BGE Reranker
* Gemini 2.5 Pro as the reasoning model
* GCP as the deployment platform

---

# 2. High-Level Solution Architecture

```text
                      ┌──────────────────────┐
                      │ Regulatory Documents │
                      │ RBI / Basel / AML    │
                      └──────────┬───────────┘
                                 │
                                 ▼
                  ┌──────────────────────────┐
                  │ Document Ingestion Layer │
                  └──────────┬───────────────┘
                             │
                             ▼
                 ┌────────────────────────────┐
                 │ Parsing & Chunking Service │
                 └──────────┬─────────────────┘
                            │
                            ▼
               ┌──────────────────────────────┐
               │ Embedding Generation Service │
               └──────────┬───────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────────┐
        │ PostgreSQL + pgvector                   │
        │                                         │
        │ • Document Metadata                     │
        │ • Version Information                   │
        │ • Chunk Repository                      │
        │ • Vector Embeddings                     │
        │ • Full Text Search Index                │
        └──────────────┬──────────────────────────┘
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      Semantic Search      BM25 Search
         (HNSW)             (GIN FTS)
             │                   │
             └─────────┬─────────┘
                       ▼
           Reciprocal Rank Fusion
                       │
                       ▼
                  Re-Ranker
                       │
                       ▼
                 Context Builder
                       │
                       ▼
                Google ADK Agent
                       │
                       ▼
             Compliance Assessment
```

---

# 3. RAG Pipeline Design

## 3.1 Document Ingestion Strategy

### Supported Formats

* PDF
* DOCX
* HTML
* Regulatory Circulars
* Regulatory Amendments
* Policy Documents
* Knowledge Articles

### Processing Framework

Recommended libraries:

```text
PyMuPDF
Unstructured.io
pdfplumber
Apache Tika
```

### Ingestion Workflow

```text
Document Upload
        │
        ▼
Format Detection
        │
        ▼
Text Extraction
        │
        ▼
Metadata Extraction
        │
        ▼
Version Detection
        │
        ▼
Chunking
        │
        ▼
Embedding Generation
        │
        ▼
Storage
```

### Metadata Captured

| Field          | Description                |
| -------------- | -------------------------- |
| document_id    | Unique document identifier |
| title          | Regulation title           |
| source         | RBI/Basel/Internal         |
| version        | Document version           |
| effective_date | Regulation effective date  |
| supersedes     | Previous version           |
| section        | Section number             |
| clause         | Clause number              |
| page_number    | Source page                |

---

# 3.2 Chunking Strategy

## Recommended Approach

Semantic Chunking

Regulatory documents contain:

* Sections
* Subsections
* Clauses
* Exceptions
* Amendments

Breaking chunks arbitrarily may destroy legal context.

### Example

```text
Section 5

Clause 5.1
Clause 5.2

Section 6

Clause 6.1
```

Chunk boundaries should align with:

* Clause boundaries
* Section boundaries
* Paragraph boundaries

### Configuration

| Parameter          | Value          |
| ------------------ | -------------- |
| Chunk Size         | 500–800 tokens |
| Overlap            | 50–100 tokens  |
| Boundary Type      | Semantic       |
| Metadata Retention | Yes            |

### Justification

Benefits:

* Preserves legal meaning
* Improves retrieval precision
* Reduces hallucinations
* Enhances citation accuracy

---

# 3.3 Embedding Model Selection

## Recommended Model

BAAI BGE Large v1.5

### Advantages

* Open Source
* Strong MTEB benchmark performance
* Excellent for finance and legal retrieval
* High semantic understanding
* Production ready

### Alternatives

| Model             | Pros                      | Cons                                 |
| ----------------- | ------------------------- | ------------------------------------ |
| BGE Large v1.5    | Highest retrieval quality | Larger memory footprint              |
| BGE Base v1.5     | Faster and cheaper        | Slightly lower accuracy              |
| Nomic Embed Text  | Fully open                | Slightly lower retrieval performance |
| OpenAI Embeddings | Strong accuracy           | Proprietary                          |

### Final Recommendation

```text
BAAI BGE Large v1.5
```

---

# 3.4 Vector Database Selection

## Candidate Evaluation

### Pinecone

Pros

* Managed service
* Excellent scalability

Cons

* Proprietary
* Additional database required

### Weaviate

Pros

* Open source
* Native hybrid search

Cons

* Additional database needed for compliance metadata

### PostgreSQL + pgvector

Pros

* Open source
* Single storage platform
* Native versioning support
* SQL support
* Audit friendly

Cons

* Requires tuning at very large scale

## Comparison

| Feature                | pgvector  | Weaviate | Pinecone |
| ---------------------- | --------- | -------- | -------- |
| Open Source            | Yes       | Yes      | No       |
| SQL Support            | Excellent | Limited  | No       |
| Versioning             | Excellent | Moderate | Moderate |
| Compliance Audit       | Excellent | Moderate | Moderate |
| Metadata Filtering     | Excellent | Good     | Good     |
| Operational Complexity | Low       | Medium   | Low      |

## Final Recommendation

```text
PostgreSQL + pgvector
```

Reason:

Provides vector search, relational metadata management, versioning, auditability, and compliance traceability within a single platform.

---

# 3.5 Retrieval Strategy

## Hybrid Retrieval

A compliance system must support:

* Exact regulation matching
* Semantic understanding

Therefore a hybrid approach is recommended.

### Step 1

Keyword Search

```text
BM25
```

Top 30 results

### Step 2

Semantic Search

```text
HNSW Vector Search
```

Top 30 results

### Step 3

Reciprocal Rank Fusion (RRF)

Combine results from both retrieval methods.

Benefits:

* Better recall
* Better precision
* Industry standard

### Step 4

Re-ranking

Recommended Model:

```text
BGE Reranker Large
```

Input:

```text
Query
Candidate Chunks
```

Output:

```text
Top 5 Relevant Chunks
```

### Step 5

Contextual Compression

Remove:

* Duplicates
* Headers
* Footers
* Noise

before sending context to the LLM.

---

# 3.6 Version Control Strategy

Compliance regulations evolve continuously.

Documents must never be overwritten.

### Recommended Model

```text
RBI Circular
        │
 ┌──────┼──────┐
 ▼      ▼      ▼
V1     V2     V3
```

### Metadata

| Field          | Description       |
| -------------- | ----------------- |
| version_number | Document version  |
| effective_from | Effective date    |
| effective_to   | Expiry date       |
| status         | Active/Superseded |
| supersedes     | Previous version  |

### Benefits

* Full audit trail
* Historical lookup
* Regulatory traceability

---

# 4. Agentic Compliance Checker

## Agent Framework

Google Agent Development Kit (ADK)

## Responsibilities

The agent must:

1. Understand transaction details
2. Query regulatory knowledge base
3. Identify applicable regulations
4. Evaluate risk
5. Generate recommendations
6. Provide citations

---

## Agent Workflow

```text
Transaction Input
        │
        ▼
Intent Analysis
        │
        ▼
RAG Retrieval
        │
        ▼
Evidence Collection
        │
        ▼
Compliance Reasoning
        │
        ▼
Structured Assessment
```

---

## Sample Input

```text
Cross-border payment of $2M
to a non-KYC entity
in a high-risk jurisdiction.
```

---

## Sample Output

```json
{
  "risk_rating": "HIGH",
  "confidence": 0.92,
  "applicable_regulations": [
    "RBI AML Guideline Section 4.2",
    "Basel III Risk Control Policy"
  ],
  "required_actions": [
    "Enhanced Due Diligence",
    "KYC Verification",
    "Compliance Officer Approval"
  ],
  "citations": [
    {
      "document": "RBI Circular 2025",
      "section": "4.2",
      "page": 12
    }
  ]
}
```

---

# 5. Recommended Technology Stack

| Layer           | Technology                  |
| --------------- | --------------------------- |
| Agent Framework | Google ADK                  |
| Backend API     | FastAPI                     |
| Vector Store    | PostgreSQL + pgvector       |
| Keyword Search  | PostgreSQL Full Text Search |
| Retrieval       | Hybrid Search               |
| Fusion          | Reciprocal Rank Fusion      |
| Re-Ranking      | BGE Reranker Large          |
| Embeddings      | BGE Large v1.5              |
| LLM             | Gemini 2.5 Pro              |
| Parsing         | PyMuPDF + Unstructured      |
| Observability   | LangSmith                   |
| Deployment      | GCP GKE / Cloud Run         |

---

# 6. Conclusion

The proposed architecture combines Hybrid Retrieval, PostgreSQL pgvector, Google ADK, and Gemini 2.5 Pro to build an explainable, auditable, and scalable Regulatory Compliance Assistant.

Key benefits include:

* Open-source-friendly architecture
* Strong retrieval accuracy
* Regulatory document versioning
* Source-attributed responses
* Auditability and traceability
* Production-ready deployment on GCP

This architecture is well-suited for regulatory compliance, AML, KYC, Basel III, and financial governance use cases.

---

# 7. Hybrid RAG Retrieval Pipeline — Deep Dive

## 7.1 Why Two Search Signals?

Both searches run against `document_chunks` in PostgreSQL, but they measure fundamentally different things:

| | Semantic Search (Dense) | Keyword Search (Sparse / FTS) |
|---|---|---|
| **How it works** | `pgvector` HNSW index + cosine similarity: `1 - (embedding <=> query_vector)` | Postgres `tsvector` / `ts_rank_cd` with `plainto_tsquery` - converts the user's text into normalized search term |
| **Strength** | Finds chunks that mean the same thing even with different words ("capital adequacy ratio" → "CAR buffer") | Finds chunks containing exact regulatory terms ("Regulation 14(3)(b)", "SARB Directive 7") |
| **Blind spot** | Can return superficially similar vectors that are off-topic; misses exact jargon | Fails completely when the user paraphrases; zero score if a single keyword is absent |

For regulatory compliance, **both signals matter**. A query like *"what are the liquidity requirements for tier-2 banks"* needs semantic understanding **and** must reliably surface a chunk that literally says "Tier 2 liquidity".

---

## 7.2 Reciprocal Rank Fusion (RRF) — Why Not Average Scores?

Each search returns up to `limit=30` candidates ranked #1–30. The scores are **incomparable** across systems: cosine similarity lives in [0,1] while `ts_rank_cd` is an uncalibrated float. Adding `0.82 + 0.003` directly is meaningless.

**RRF solves this by ignoring raw scores and using only rank position:**

```
RRF(chunk) = Σ  1 / (60 + rank_in_list)
```

The constant `60` is the standard RRF smoothing parameter (Cormack et al.). It dampens the outsized advantage of rank #1 vs rank #2.

**What RRF achieves:**

* A chunk ranked **#1 semantic + #1 keyword** gets the maximum RRF score ≈ `1/61 + 1/61 ≈ 0.033`
* A chunk appearing **only** in semantic at rank #5 gets `1/65 ≈ 0.015`
* A chunk appearing in **both lists** at moderate ranks #8 and #12 gets `1/68 + 1/72 ≈ 0.028` — beating a single-list rank #2

Cross-list consensus is a strong quality signal. A chunk validated by two independent retrieval mechanisms is far more likely to be relevant than one highly ranked by only one.

---

## 7.3 Cross-Encoder Reranker (BGEReranker) — Why Not Stop at RRF?

RRF produces the top ~20 candidates in a sensible order, but it has a fundamental limitation: **it never reads the query and chunk together**. It only knows rank positions from each list independently.

The `BGEReranker` uses `BAAI/bge-reranker-large`, a **cross-encoder** architecture:

```
Input:  [CLS] query [SEP] chunk_text [SEP]
Output: single relevance logit
```

| | Bi-encoder (Dense Search) | Cross-encoder (Reranker) |
|---|---|---|
| **Encodes** | query and chunk **separately** | query and chunk **jointly** |
| **Can model** | rough semantic overlap | fine-grained relevance: negation, entity specificity, conditional clauses |
| **Speed** | Fast — embeddings pre-computed at index time | Slower — inference per (query, chunk) pair at query time |
| **Purpose** | Recall — fetch broad candidates | Precision — reorder top-N |

The cross-encoder can distinguish *"Basel III Pillar 2 capital surcharge"* from *"Basel III Pillar 1 minimum capital"* even when both have near-identical embedding vectors, because it reads both texts in a single joint forward pass.

---

## 7.4 Full Pipeline Summary


```text
User Query
    │
    ├──────────────────────────────────────┐
    ▼                                      ▼
Semantic Search                     Keyword Search
(pgvector HNSW)                  (Postgres FTS / tsvector)
Top-30 by cosine similarity       Top-30 by ts_rank_cd
    │                                      │
    └──────────────┬───────────────────────┘
                   ▼
          Reciprocal Rank Fusion
          score = Σ 1 / (60 + rank)
          → Top-20 merged candidates
                   │
                   ▼
        Cross-Encoder Reranker
        BAAI/bge-reranker-large
        joint (query, chunk) scoring
                   │
                   ▼
     Context Compression & Deduplication
     (remove duplicate overlapping windows)
                   │
                   ▼
        Top-5 Chunks → LLM Context
```

| Stage | Problem Solved | Output |
|---|---|---|
| Semantic search | Paraphrase and conceptual queries | 30 candidates by meaning |
| Keyword search | Exact regulatory citations and jargon | 30 candidates by term match |
| RRF | Incompatible score scales; rewards multi-signal consensus | 20 merged, rank-fused candidates |
| Cross-encoder reranker | Bi-encoder embeddings cannot model fine-grained joint relevance | Top-N reordered by true relevance |
| Deduplication | Overlapping chunk windows produce near-duplicates | Final 5 unique chunks |

---

# 8. Worked Example — Pipeline Trace with Sample Data

## 8.1 Sample Corpus

The following 6 chunks exist in `document_chunks`:

| ID | Chunk Text (abbreviated) |
|----|--------------------------|
| C1 | *"Regulation 14(3)(b): A bank shall maintain a Liquidity Coverage Ratio (LCR) of not less than 100% at all times..."* |
| C2 | *"Capital adequacy requirements under Basel III mandate a minimum Common Equity Tier 1 (CET1) ratio of 4.5% of risk-weighted assets..."* |
| C3 | *"The net stable funding ratio (NSFR) requires banks to maintain stable funding sources relative to their liquidity profile over a one-year horizon..."* |
| C4 | *"Pillar 2 supervisory review allows the SARB to impose additional capital buffers beyond the Pillar 1 minimum requirements..."* |
| C5 | *"Banks must ensure sufficient liquid assets are held to cover net cash outflows over a 30-day stress period under LCR obligations..."* |
| C6 | *"Credit risk-weighted assets must be computed using either the standardised approach or the internal ratings-based (IRB) approach..."* |

---

## 8.2 Query: `"what are the liquidity requirements for banks"`

### Stage 1 — Semantic Search Results (cosine similarity)

| Rank | Chunk | Similarity Score |
|------|-------|-----------------|
| 1 | C5 | 0.91 |
| 2 | C1 | 0.87 |
| 3 | C3 | 0.82 |
| 4 | C4 | 0.61 |
| 5 | C2 | 0.55 |
| 6 | C6 | 0.41 |

> C4 ("Pillar 2 capital buffers") and C2 ("CET1 ratio") received non-zero scores because "requirements" and "banks" are semantically nearby — false positives that pure vector search cannot filter.

### Stage 1 — Keyword Search Results (ts_rank_cd)

`plainto_tsquery('english', 'liquidity requirements banks')` matches:

| Rank | Chunk | ts_rank Score |
|------|-------|--------------|
| 1 | C1 | 0.0821 |
| 2 | C3 | 0.0612 |
| 3 | C5 | 0.0589 |
| 4 | C2 | 0.0201 |
| — | C4 | *(no match — "liquidity" absent)* |
| — | C6 | *(no match)* |

> C4 drops out entirely. The keyword system's silence is a credible negative signal.

---

### Stage 2 — RRF Fusion

```
RRF(chunk) = 1/(60 + semantic_rank) + 1/(60 + keyword_rank)
             (0 contribution if absent from a list)
```

| Chunk | Semantic Rank | Keyword Rank | RRF Calculation | RRF Score |
|-------|:---:|:---:|---|:---:|
| C5 | 1 | 3 | `1/61 + 1/63` | **0.03232** |
| C1 | 2 | 1 | `1/62 + 1/61` | **0.03228** |
| C3 | 3 | 2 | `1/63 + 1/62` | **0.03224** |
| C2 | 5 | 4 | `1/65 + 1/64` | **0.03108** |
| C4 | 4 | *(absent)* | `1/64 + 0` | **0.01563** |
| C6 | 6 | *(absent)* | `1/66 + 0` | **0.01515** |

**RRF-sorted order: C5 → C1 → C3 → C2 → C4 → C6**

Key observations:
- **C5 wins** because it ranked well in *both* lists — multi-signal consensus rewarded
- **C4 collapses** from semantic rank #4 to overall rank #5 — keyword silence penalised it
- **Scores could not simply be compared raw**: 0.55 (cosine, C2) vs 0.61 (cosine, C4) would have kept C4 ahead, but RRF correctly demotes it

---

### Stage 3 — Cross-Encoder Reranker

BGE-large receives each `[query, chunk]` pair jointly and outputs a single relevance logit:

| Chunk | RRF Rank | Reranker Logit | Final Rank |
|-------|:---:|:---:|:---:|
| C1 | 2 | **4.82** | **1** |
| C5 | 1 | **4.71** | **2** |
| C3 | 3 | **4.10** | **3** |
| C2 | 4 | **-1.23** | **4** |
| C4 | 5 | **-2.87** | **5** |
| C6 | 6 | **-3.41** | **6** |

What the cross-encoder detected that RRF could not:
- **C1 jumps to #1** — reading *"Regulation 14(3)(b): A bank shall maintain a Liquidity Coverage Ratio of not less than 100%"* jointly with the query, the model recognises this is the **authoritative definitional source** of the liquidity requirement
- **C2 collapses to -1.23** — reading "CET1 ratio of 4.5%" alongside "liquidity requirements", the model correctly classifies this as a **capital** question, not a liquidity question. The word "requirements" was a false positive that RRF had no mechanism to detect
- **C4 at -2.87** — Pillar 2 capital buffers are correctly scored as entirely off-topic

---

### Stage 4 — Final Output to the LLM (top 5 after deduplication)

```
1. C1 — Regulation 14(3)(b) LCR definition         [rerank: 4.82]
2. C5 — LCR 30-day stress period obligations        [rerank: 4.71]
3. C3 — NSFR one-year stable funding requirement    [rerank: 4.10]
4. C2 — Basel III CET1 capital adequacy             [rerank: -1.23]
5. C4 — Pillar 2 supervisory capital buffers        [rerank: -2.87]
```

C6 is excluded by the top-5 cutoff. In this small 6-chunk example, C2 and C4 are still included but strongly demoted by the cross-encoder, reducing their influence versus C1/C5/C3.

---

## 8.3 Why Each Stage Was Necessary in This Example

| Without... | What would have gone wrong |
|---|---|
| Keyword search | C1 (`Regulation 14(3)(b)`) might rank lower — the exact regulatory citation is what boosted it in FTS |
| RRF | Without rank-based fusion, C4 would stay relatively high on semantic similarity alone (raw cosine 0.61), even though keyword search gives it no support — and raw scores from two different systems cannot be meaningfully merged |
| Cross-encoder | Without cross-encoder reranking, C2 and C4 would rank higher than they should; reranking pushes them down and keeps the true liquidity chunks (C1/C5/C3) on top, reducing capital-topic contamination |
