# CORA SARB Decision Brief (One Page)

Date: 2026-06-10
Audience: Architecture Review Board, Security, Platform, Compliance, Product

## 1) Decision Request

Approve CORA for controlled production readiness execution with conditional gates.

Requested decision:

- Approve architecture direction and phased rollout plan.
- Require completion of mandatory controls before production go-live.

## 2) What CORA Delivers

CORA is an AI-enabled compliance platform that provides:

- Regulatory Q&A with evidence and citations
- Transaction screening and risk rationale
- Regulatory change impact analysis
- Compliance report generation
- Audit-oriented traceability

Business value:

- Faster compliance operations
- Better consistency in interpretations
- Improved audit preparedness and explainability

## 3) Current Architecture Snapshot

Core runtime:

- Frontend: React + TypeScript
- API: FastAPI service boundary
- Agentic backend: ADK root + specialized subagents
- Data: PostgreSQL + pgvector
- Deployment baseline: Docker + Kubernetes manifests

Status:

- Core service decomposition and RAG workflow are implemented.
- Production-hardening controls are partially implemented.

## 4) Decision Drivers

1. Strong alignment with compliance use cases and personas.
2. Clear bounded architecture and extensible agent pattern.
3. Traceability-first design with citations and audit pathway.
4. Practical deployment foundation already in repository.

## 5) Key Risks and Conditions

Top risks:

- Missing enterprise authN/authZ controls in core paths
- In-process worker coupling (ingestion/reporting) can affect scalability
- Partial observability for production incident response
- Local document storage still present in current implementation

Mandatory conditions before production go-live:

1. Enforce authentication and RBAC authorization.
2. Add centralized logs, metrics, tracing, and alerting.
3. Decouple async workloads using queue-backed workers.
4. Move document storage to managed object storage.
5. Complete security baseline (identity, network, encryption, audit retention).

## 6) Recommended Board Decision

Decision: Approve with conditions.

Approval scope:

- Approve target architecture and delivery roadmap.
- Approve phased hardening approach.

Go-live gate:

- Production release only after all mandatory conditions are verified and signed off by Architecture, Security, Platform/SRE, and Compliance.

## 7) 90-Day Execution Plan

Phase 1 (Weeks 1-4): Foundation Hardening

- Implement authN/authZ
- Add end-to-end observability
- Validate audit trace correlation

Phase 2 (Weeks 5-8): Runtime Decoupling

- Introduce queue and worker deployments
- Externalize ingestion and report workflows
- Add retry and dead-letter controls

Phase 3 (Weeks 9-12): Production Readiness

- Migrate storage to managed service
- Complete security controls and policy checks
- Run load, resilience, and release gate validation

## 8) Decision Checklist

Required sign-offs:

- Architecture
- Security
- Platform/SRE
- Compliance/Legal
- Product

Release criteria summary:

- No open high or critical security findings
- AuthN/authZ enforced
- Observability operational
- Audit traceability validated
- Performance and resilience targets met

## 9) Supporting Documents

- docs/Architecture_Document.md
- docs/Architecture_Stakeholder_Review.md
- README.md
