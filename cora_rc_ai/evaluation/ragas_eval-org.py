"""
Automated Evaluation Script using RAGAS and LangSmith.
Evaluates the CORA RAG pipeline based on:
- context_precision
- context_recall
- faithfulness
- answer_relevancy
"""
import os
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from contextlib import nullcontext
from uuid import uuid4

# Disable LangChain/LangSmith background tracing before importing ragas/langchain.
# The configured hosted key returns 403, and auto-tracing (LANGSMITH_TRACING=true in
# .env) would otherwise flood every LLM call with ingest errors.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

import pandas as pd
from datasets import Dataset
from ragas import RunConfig, evaluate
from ragas.metrics import (
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy,
)
from ragas.llms import LangchainLLMWrapper
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langsmith import Client as LangSmithClient


# Initialize LangSmith client (reads LANGSMITH_API_KEY from env automatically)
ls_client = LangSmithClient(
    api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
    api_key=os.getenv("LANGSMITH_API_KEY"),
)
LS_PROJECT = os.getenv("LANGSMITH_PROJECT", "cora-rc-ai")

# Evaluator LLM (adjust model to your local/runtime setup)
eval_llm = ChatOllama(model=os.getenv("RAGAS_EVAL_MODEL", "llama3.1:8b"), temperature=0)
evaluator_llm = LangchainLLMWrapper(eval_llm)

# Embeddings for evaluation
embeddings = HuggingFaceEmbeddings(
    model_name=os.getenv("RAGAS_EMBED_MODEL", "BAAI/bge-large-en-v1.5")
)

# Fallback sample dataset if no external evalset is found
FALLBACK_TEST_DATA = {
    "question": [
        "What is the full title of the RBI KYC master direction updated on August 14, 2025?",
        "Which chapter in the RBI KYC Direction, 2016 covers Customer Acceptance Policy?",
        "Which major parts are listed under Chapter VI of the RBI KYC Direction, 2016?",
        "What is the full title of the RBI commercial banks KYC direction issued in 2025?",
        "Which due diligence topics are explicitly listed in Chapter VI of the RBI commercial banks KYC directions, 2025?",
        "What is the full title of the RBI 2025 directions on transfer and distribution of credit risk for NBFCs?",
        "What are the major parts covered by the RBI 2025 directions on transfer and distribution of credit risk?",
        "What is the stated purpose of the RBI 2025 credit risk transfer framework?",
        "Which sections and chapters are prominently listed in the NBFC-NSI-ND master direction, 2016?",
        "According to the NBFC liquidity risk management framework, what must the Board ensure?",
        "What categories of NPAs are listed in the prudential norms circular on income recognition, asset classification and provisioning?",
        "What core topics are covered in the prudential norms master circular pertaining to advances?"
    ],
    "answer": [
        "The document is titled 'Master Direction - Know Your Customer (KYC) Direction, 2016 (Updated as on August 14, 2025)'.",
        "Customer Acceptance Policy is covered in Chapter III of the RBI KYC Direction, 2016.",
        "Chapter VI covers Customer Due Diligence (CDD) procedure in case of individuals, CDD measures for sole proprietary firms, CDD measures for legal entities, identification of beneficial owner, on-going due diligence, and enhanced and simplified due diligence procedure.",
        "The document is titled 'Reserve Bank of India (Commercial Banks - Know Your Customer) Directions, 2025 (Updated as on December 29, 2025)'.",
        "The RBI commercial banks KYC directions list the following due diligence topics in Chapter VI: CDD procedure in case of individuals, CDD measures for sole proprietary firms, CDD measures for legal entities, identification of beneficial owner, on-going due diligence, enhanced due diligence, and simplified due diligence.",
        "The document is titled 'Reserve Bank of India (Non-Banking Financial Companies - Transfer and Distribution of Credit Risk) Directions, 2025'.",
        "The directions cover Part A - Transfer of Loan Exposures, Part B - Co-lending Arrangements, and Part C - Repeal and Other Provisions.",
        "The framework is described as a comprehensive and self-contained framework of regulatory guidelines governing different avenues of credit risk transfer and distribution.",
        "The NBFC-NSI-ND master direction prominently lists Section I: Introduction, Chapter I - Preliminary, Chapter II - Definition, Chapter III - Registration, Section II: Prudential Issues, Chapter IV - Prudential Regulations, Chapter V - Fair Practice Code, Section III: Governance Issues, Chapter IX - Acquisition/Transfer of Control, and Section IV: Miscellaneous Issues including Chapter XII - Reporting Requirements.",
        "The Board must frame a liquidity risk management framework that ensures the NBFC maintains sufficient liquidity, including a cushion of unencumbered, high quality liquid assets to withstand a range of stress events, and that sets out liquidity risk tolerance, funding strategies, prudential limits, measurement, reporting, stress testing, and contingency funding planning.",
        "The prudential norms circular lists the categories of NPAs as substandard assets, doubtful assets, and loss assets.",
        "The prudential norms master circular covers income recognition, asset classification, and provisioning pertaining to advances."
    ],
    "contexts": [
        [
            "Master Direction - Know Your Customer (KYC) Direction, 2016 ( Updated as on August 14, 2025 )"
        ],
        [
            "Contents ... CHAPTER III Customer Acceptance Policy ..."
        ],
        [
            "Chapter VI Customer Due Diligence (CDD) Procedure Part I - Customer Due Diligence (CDD) Procedure in case of Individuals Part II - CDD Measures for Sole Proprietary firms Part III - CDD Measures for Legal Entities Part IV - Identification of Beneficial Owner Part V - On-going Due Diligence Part VI - Enhanced and Simplified Due Diligence Procedure"
        ],
        [
            "Reserve Bank of India (Commercial Banks - Know Your Customer) Directions, 2025 (Updated as on December 29, 2025)"
        ],
        [
            "Chapter VI - Customer Due Diligence (CDD) Procedure A. CDD Procedure in case of Individuals B. CDD Measures for Sole Proprietary firms C. CDD Measures for Legal Entities D. Identification of Beneficial Owner E. On-going Due Diligence F. Enhanced and Simplified Due Diligence Procedure F.1 Enhanced Due Diligence F.2 Simplified Due Diligence"
        ],
        [
            "Reserve Bank of India (Non-Banking Financial Companies - Transfer and Distribution of Credit Risk) Directions, 2025"
        ],
        [
            "PART A - TRANSFER OF LOAN EXPOSURES ... PART B: CO-LENDING ARRANGEMENTS ... PART C: REPEAL AND OTHER PROVISIONS"
        ],
        [
            "Credit Risk Transfer and Distributions are resorted to by lending institutions for multitude of reasons ranging from liquidity management and rebalancing their exposures or strategic sales ... the Reserve Bank hereby issues a comprehensive and self-contained framework of regulatory guidelines governing different avenues of credit risk transfer and distribution."
        ],
        [
            "Index Section I : Introduction Chapter I - Preliminary Chapter II - Definition Chapter III - Registration Section II : Prudential Issues Chapter IV - Prudential Regulations Chapter V - Fair Practice Code ... Section III: Governance Issues Chapter IX - Acquisition/Transfer of Control ... Chapter XII - Reporting Requirements"
        ],
        [
            "In order to ensure a sound and robust liquidity risk management system, the Board of the NBFC shall frame a liquidity risk management framework which ensures that it maintains sufficient liquidity, including a cushion of unencumbered, high quality liquid assets to withstand a range of stress events ... entity-level liquidity risk tolerance; funding strategies; prudential limits; system for measuring, assessing and reporting/reviewing liquidity; framework for stress testing; liquidity planning under alternative scenarios/formal contingent funding plan."
        ],
        [
            "4 ASSET CLASSIFICATION 4.1 Categories of NPAs 4.1.1 Substandard Assets 4.1.2 Doubtful Assets 4.1.3 Loss Assets"
        ],
        [
            "Master Circular - Prudential norms on Income Recognition, Asset Classification and Provisioning pertaining to Advances"
        ]
    ],
    "ground_truth": [
        "The full title is 'Master Direction - Know Your Customer (KYC) Direction, 2016 (Updated as on August 14, 2025)'.",
        "Customer Acceptance Policy is in Chapter III.",
        "Chapter VI includes CDD for individuals, sole proprietary firms, legal entities, beneficial owner identification, on-going due diligence, and enhanced/simplified due diligence.",
        "The full title is 'Reserve Bank of India (Commercial Banks - Know Your Customer) Directions, 2025 (Updated as on December 29, 2025)'.",
        "Chapter VI lists individuals, sole proprietary firms, legal entities, beneficial owner identification, on-going due diligence, enhanced due diligence, and simplified due diligence.",
        "The full title is 'Reserve Bank of India (Non-Banking Financial Companies - Transfer and Distribution of Credit Risk) Directions, 2025'.",
        "The major parts are Transfer of Loan Exposures, Co-lending Arrangements, and Repeal and Other Provisions.",
        "It is a comprehensive and self-contained framework governing credit risk transfer and distribution.",
        "The direction lists sections on introduction, definitions, registration, prudential issues, fair practice, governance issues including acquisition/transfer of control, and reporting requirements.",
        "The Board must ensure a documented liquidity risk management framework with sufficient liquidity and controls such as risk tolerance, funding strategy, prudential limits, reporting, stress testing, and contingency planning.",
        "The NPA categories are substandard assets, doubtful assets, and loss assets.",
        "The circular covers income recognition, asset classification, and provisioning for advances."
    ],
    "category": [
        "AML_KYC",
        "AML_KYC",
        "AML_KYC",
        "AML_KYC",
        "AML_KYC",
        "Credit_Risk_Transfer",
        "Credit_Risk_Transfer",
        "Credit_Risk_Transfer",
        "NBFC_Prudential_Framework",
        "NBFC_Prudential_Framework",
        "Prudential_Norms",
        "Prudential_Norms"
    ],
    "source_document": [
        "Master-Direction-Know-Your-Customer(KYC)Direction-2016-updated-August-14-2025.pdf",
        "Master-Direction-Know-Your-Customer(KYC)Direction-2016-updated-August-14-2025.pdf",
        "Master-Direction-Know-Your-Customer(KYC)Direction-2016-updated-August-14-2025.pdf",
        "169MD.pdf",
        "169MD.pdf",
        "RBI-DOR-2025-26-352_23122025162847657.pdf",
        "RBI-DOR-2025-26-352_23122025162847657.pdf",
        "RBI-DOR-2025-26-352_23122025162847657.pdf",
        "RBI-MASTER-DIRECTION-NBFC-NSI-ND-29-08-23.pdf",
        "RBI-MASTER-DIRECTION-NBFC-NSI-ND-29-08-23.pdf",
        "Prudential norms.pdf",
        "Prudential norms.pdf"
    ]
}


def _load_evalset() -> dict:
    """
    Load evalset from EVALSET_PATH if present.
    Supported formats: JSON with keys question, answer, contexts, ground_truth.
    Falls back to built-in sample data.
    """
    evalset_path = os.getenv("EVALSET_PATH", "").strip()
    if not evalset_path:
        return FALLBACK_TEST_DATA

    path = Path(evalset_path)
    if not path.exists():
        print(f"Evalset not found at {path}. Using fallback sample.")
        return FALLBACK_TEST_DATA

    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        required = {"question", "answer", "contexts", "ground_truth"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"Evalset missing required fields: {sorted(missing)}")
        return data

    raise ValueError("Unsupported evalset format. Use JSON with required RAGAS fields.")


def _eval_observation_context(rows: int):
    """
    No-op context manager — LangSmith tracing happens via explicit run logging below.
    Kept for structural compatibility with the original flow.
    """
    return nullcontext(None)


async def _run_agent(runner, session_service, app_name: str, question: str) -> str:
    """Run the compliance agent once and return its final text answer."""
    from google.genai.types import Content, Part  # noqa: PLC0415

    user_id = "eval_user"
    session_id = str(uuid4())
    await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    user_message = Content(role="user", parts=[Part.from_text(text=question)])

    full_response = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=user_message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            full_response = "".join(p.text for p in event.content.parts if p.text)
    return full_response


async def _populate_live(test_data: dict) -> dict:
    """
    Replace the static `contexts` and `answer` columns with values produced by the
    REAL pipeline: contexts from HybridRetriever, answers from the compliance agent.
    `ground_truth`/`question` are kept from the evalset. Enabled with LIVE_EVAL=true.
    """
    # Mirror backend startup env so cached models load offline and ADK doesn't probe
    # Google metadata. setdefault keeps any values already set by the user/.env.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
    os.environ.setdefault("GOOGLE_API_KEY", "local-ollama-no-google-api")

    from cora_rc_ai.backend_agentic.tools.rag_tool import get_retriever  # noqa: PLC0415
    from cora_rc_ai.backend_agentic.agents.compliance_agent import compliance_agent  # noqa: PLC0415
    from google.adk.runners import Runner  # noqa: PLC0415
    from google.adk.sessions.in_memory_session_service import (  # noqa: PLC0415
        InMemorySessionService,
    )

    app_name = "cora_eval"
    retriever = get_retriever()
    session_service = InMemorySessionService()
    runner = Runner(
        app_name=app_name, agent=compliance_agent, session_service=session_service
    )

    retrieve_limit = int(os.getenv("LIVE_RETRIEVE_LIMIT", "5"))
    questions = test_data["question"]
    live_contexts: list = []
    live_answers: list = []

    for i, question in enumerate(questions):
        # 1. Real retrieval → contexts
        try:
            chunks = retriever.retrieve(question, limit=retrieve_limit)
            contexts = [c.get("chunk_text", "") for c in chunks if c.get("chunk_text")]
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}] retrieval failed: {exc}")
            contexts = []
        live_contexts.append(contexts or [""])  # ragas needs a non-empty list

        # 2. Real agent → answer
        try:
            answer = await _run_agent(runner, session_service, app_name, question)
        except Exception as exc:  # noqa: BLE001
            print(f"[{i}] agent failed: {exc}")
            answer = ""
        live_answers.append(answer)

        print(f"[{i + 1}/{len(questions)}] live pipeline done for: {question[:60]}...")

    data = dict(test_data)
    data["contexts"] = live_contexts
    data["answer"] = live_answers
    return data


async def run_evaluation():
    print("Starting CORA RAGAS Evaluation...")

    test_data = _load_evalset()

    if os.getenv("LIVE_EVAL", "false").lower() == "true":
        print("LIVE_EVAL enabled — querying the real retriever + compliance agent...")
        test_data = await _populate_live(test_data)
    else:
        print(
            "LIVE_EVAL disabled — scoring static gold contexts/answers. "
            "Set LIVE_EVAL=true to evaluate the real pipeline."
        )

    dataset = Dataset.from_dict(test_data)

    run_config = RunConfig(
        timeout=int(os.getenv("RAGAS_TIMEOUT", "600")),
        max_workers=int(os.getenv("RAGAS_MAX_WORKERS", "2")),
    )
    with _eval_observation_context(len(test_data["question"])) as eval_span:
        result = evaluate(
            dataset,
            metrics=[
                context_precision,
                context_recall,
                faithfulness,
                answer_relevancy,
            ],
            llm=evaluator_llm,
            embeddings=embeddings,
            run_config=run_config,
        )

        if eval_span is not None and hasattr(eval_span, "update"):
            eval_span.update(
                output={"status": "completed"},
                metadata={
                    "metrics": [
                        "context_precision",
                        "context_recall",
                        "faithfulness",
                        "answer_relevancy",
                    ]
                },
            )

        df = result.to_pandas()

    # Show all columns in the console (no '...' truncation) and persist the full
    # results so they can be inspected later without re-running the evaluation.
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 60)
    out_path = Path(__file__).parent / "ragas_results.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved full results to {out_path}")

    # RAGAS >=0.2 renames columns: question->user_input, answer->response,
    # ground_truth->reference. Select whatever is present to stay robust.
    metric_cols = ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]
    print("\n=== Evaluation Results ===")
    display_cols = [c for c in (["user_input"] + metric_cols) if c in df.columns]
    print(df[display_cols])

    present_metrics = [c for c in metric_cols if c in df.columns]
    if present_metrics:
        print("\n=== Mean Scores ===")
        print(df[present_metrics].mean().round(4).to_string())

    # Optional LangSmith logging. Off by default (current key returns 403). Enable with
    # ENABLE_LANGSMITH_LOGGING=true and a valid key. Stops after first error to avoid spam.
    if os.getenv("ENABLE_LANGSMITH_LOGGING", "false").lower() == "true":
        print("\nLogging results to LangSmith...")
        for _, row in df.iterrows():
            try:
                run_id = uuid4()
                start = datetime.now(tz=timezone.utc)
                ls_client.create_run(
                    id=run_id,
                    name="CORA RAG Evaluation",
                    run_type="chain",
                    inputs={"question": row.get("user_input")},
                    project_name=LS_PROJECT,
                    start_time=start,
                )
                ls_client.update_run(
                    run_id=run_id,
                    outputs={"answer": row.get("response"), "ground_truth": row.get("reference")},
                    end_time=datetime.now(tz=timezone.utc),
                )
                for metric in present_metrics:
                    ls_client.create_feedback(
                        run_id=run_id, key=metric,
                        score=float(row[metric]), source_info={"evaluator": "ragas"},
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"Warning: stopping LangSmith logging after error: {exc}")
                break
        print("LangSmith logging done for project:", LS_PROJECT)
    else:
        print("\nLangSmith logging disabled — set ENABLE_LANGSMITH_LOGGING=true with a valid key.")

    print("Evaluation complete.")


if __name__ == "__main__":
    asyncio.run(run_evaluation())