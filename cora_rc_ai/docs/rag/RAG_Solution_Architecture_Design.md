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
