"""Runtime configuration — the single source of truth for evaluation settings.

``EvalConfig`` reads everything from the environment once (``from_env``) so the rest of
the package depends on a plain, typed object instead of scattered ``os.getenv`` calls.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Importing env_setup guarantees tracing/offline env is applied before anything that
# transitively imports ragas/langchain reads it.
from cora_rc_ai.evaluation import env_setup  # noqa: F401

# RAGAS metrics evaluated by this framework, in display order.
METRIC_NAMES = ("context_precision", "context_recall", "faithfulness", "answer_relevancy")


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EvalConfig:
    """Immutable snapshot of all evaluation settings."""

    # Models
    eval_model: str
    embed_model: str

    # Dataset
    evalset_path: str

    # Live pipeline
    live_eval: bool
    live_retrieve_limit: int
    app_name: str

    # RAGAS run tuning
    ragas_timeout: int
    ragas_max_workers: int

    # Output
    results_path: Path

    # LangSmith
    enable_langsmith_logging: bool
    langsmith_endpoint: str
    langsmith_api_key: str | None
    langsmith_project: str

    @classmethod
    def from_env(cls) -> "EvalConfig":
        results_path = Path(__file__).parent / "ragas_results.csv"
        return cls(
            eval_model=os.getenv("RAGAS_EVAL_MODEL", "llama3.1:8b"),
            embed_model=os.getenv("RAGAS_EMBED_MODEL", "BAAI/bge-large-en-v1.5"),
            evalset_path=os.getenv("EVALSET_PATH", "").strip(),
            live_eval=_as_bool(os.getenv("LIVE_EVAL", "false")),
            live_retrieve_limit=int(os.getenv("LIVE_RETRIEVE_LIMIT", "5")),
            app_name=os.getenv("EVAL_APP_NAME", "cora_eval"),
            ragas_timeout=int(os.getenv("RAGAS_TIMEOUT", "600")),
            ragas_max_workers=int(os.getenv("RAGAS_MAX_WORKERS", "2")),
            results_path=results_path,
            enable_langsmith_logging=_as_bool(os.getenv("ENABLE_LANGSMITH_LOGGING", "false")),
            langsmith_endpoint=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
            langsmith_api_key=os.getenv("LANGSMITH_API_KEY"),
            langsmith_project=os.getenv("LANGSMITH_PROJECT", "cora-rc-ai"),
        )
