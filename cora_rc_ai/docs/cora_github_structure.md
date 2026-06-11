---
title: "CORA – GitHub Folder Structure & Architecture Alignment"
author: "Arun S.P"
last_updated: "2026-06-10"
---

The Project Folder Structure

`C:\Workspace\SPR-WS\cora-rc-ai\cora_rc_ai`.



***

# CORA - Current GitHub Folder Structure 

```
cora_rc_ai/
|
|-- .env
|-- .env.example
|-- Makefile
|-- README.md
|-- __init__.py
|
|-- backend_agentic/
|   |-- __init__.py
|   |-- Dockerfile
|   |-- main.py
|   |-- requirements.txt
|   |
|   |-- agents/
|   |   |-- __init__.py
|   |   |-- compliance_agent.py
|   |   |-- dependencies.py
|   |   |
|   |   |-- prompts/
|   |   |   |-- __init__.py
|   |   |   |-- change_impact_prompt.py
|   |   |   |-- report_prompt.py
|   |   |   |-- retrieval_prompt.py
|   |   |   |-- risk_prompt.py
|   |   |   `-- root_prompt.py
|   |   |
|   |   `-- subagents/
|   |       |-- __init__.py
|   |       |-- change_impact_agent.py
|   |       |-- report_agent.py
|   |       |-- retrieval_agent.py
|   |       `-- risk_agent.py
|   |
|   |-- models/
|   |   |-- __init__.py
|   |   |-- embeddings_model.py
|   |   `-- llm_router.py
|   |
|   |-- rag/
|   |   |-- __init__.py
|   |   |-- ingestion/
|   |   `-- retrieval/
|   |
|   `-- tools/
|       |-- __init__.py
|       |-- citation_tool.py
|       |-- rag_tool.py
|       `-- risk_calculator.py
|
|-- backend_api/
|   |-- __init__.py
|   |-- Dockerfile
|   |-- main.py
|   |-- requirements.txt
|   |
|   |-- api/
|   |   |-- __init__.py
|   |   `-- v1/
|   |       |-- __init__.py
|   |       |-- audit.py
|   |       |-- chats.py
|   |       |-- health.py
|   |       |-- regulations.py
|   |       |-- reports.py
|   |       `-- transactions.py
|   |
|   |-- core/
|   |   |-- __init__.py
|   |   |-- config.py
|   |   `-- database.py
|   |
|   `-- uploads/
|       `-- regulations/
|
|-- data_layer/
|   |-- __init__.py
|   |
|   |-- postgres/
|   |   |-- schema.sql
|   |   |-- schemaV2.sql
|   |   `-- verification.sql
|   |
|   `-- vector_store/
|       |-- __init__.py
|       `-- pgvector_adapter.py
|
|-- docs/
|   |-- AI_Architect_Assignment.pdf
|   |-- cora-ai.md
|   |-- cora_github_structure.md
|   |-- Google_ADK_with_Runner_Usage.md
|   |
|   |-- architecture-diagrams/
|   |-- rag/
|   `-- ui-mockup-screenshots/
|
|-- evaluation/
|   |-- __init__.py
|   |-- config.py
|   |-- data_sources.py
|   |-- env_setup.py
|   |-- eval-requirements.txt
|   |-- evaluator.py
|   |-- live_pipeline.py
|   |-- orchestrator.py
|   |-- ragas_eval-org.py
|   |-- ragas_eval.py
|   |-- ragas_results-GoldData.csv
|   |-- ragas_results-RealData.csv
|   |-- README.md
|   |-- reporters.py
|   `-- sample_data.py
|
|-- frontend/
|   |-- Dockerfile
|   |-- README.md
|   |-- index.html
|   |-- nginx.conf
|   |-- package.json
|   |-- package-lock.json
|   |-- eslint.config.js
|   |-- postcss.config.js
|   |-- tailwind.config.js
|   |-- tsconfig.json
|   |-- tsconfig.app.json
|   |-- tsconfig.node.json
|   |-- vite.config.ts
|   |
|   |-- public/
|   `-- src/
|       |-- App.css
|       |-- App.tsx
|       |-- index.css
|       |-- main.tsx
|       |-- assets/
|       |-- components/
|       |-- pages/
|       |-- services/
|       `-- store/
|
`-- k8s/
        |-- backend-agentic.yaml
        |-- backend-api.yaml
        `-- frontend.yaml
```

***

# Architecture Alignment (Current)

### Frontend (`frontend/`)

- React + Vite TypeScript UI
- Communicates with API backend
- Supports chat views, pages, and state via `src/store/`

### Backend API (`backend_api/`)

- FastAPI entrypoint (`main.py`)
- Versioned endpoints in `api/v1/`
- Core configuration/database wiring in `core/`
- Upload area for regulations in `uploads/regulations/`

### Backend Agentic (`backend_agentic/`)

- ADK-based orchestration under `agents/`
- Specialized subagents under `agents/subagents/`
- Prompt templates under `agents/prompts/`
- RAG pipeline under `rag/` with ingestion/retrieval layers
- Tooling under `tools/` and model routing under `models/`

### Data Layer (`data_layer/`)

- PostgreSQL schemas in `postgres/`
- Vector adapter in `vector_store/pgvector_adapter.py`

### Deployment and Ops

- Kubernetes manifests in `k8s/`
- Service-level Dockerfiles in `frontend/`, `backend_api/`, and `backend_agentic/`

***

# High-Level Flow

```
Frontend (React)
        -> Backend API (FastAPI)
        -> Backend Agentic (ADK Agents + RAG)
        -> Data Layer (PostgreSQL + pgvector)
```

***
