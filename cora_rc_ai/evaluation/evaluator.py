"""RAGAS scoring — turns a dataset dict into a scored results DataFrame.

This module owns the heavy ragas/langchain imports. ``env_setup`` (imported transitively
via ``config``) has already disabled tracing and forced offline models by the time these
imports run.
"""
from __future__ import annotations

import pandas as pd
from datasets import Dataset
from ragas import RunConfig, evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

try:  # prefer the maintained packages; fall back to langchain_community if unavailable
    from langchain_ollama import ChatOllama
except ImportError:  # pragma: no cover
    from langchain_community.chat_models import ChatOllama
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:  # pragma: no cover
    from langchain_community.embeddings import HuggingFaceEmbeddings

from cora_rc_ai.evaluation.config import EvalConfig

_METRICS = [context_precision, context_recall, faithfulness, answer_relevancy]


class RagasEvaluator:
    """Scores a RAGAS dataset with a local Ollama evaluator LLM + HF embeddings."""

    def __init__(self, config: EvalConfig):
        self._config = config
        self._evaluator_llm = LangchainLLMWrapper(
            ChatOllama(model=config.eval_model, temperature=0)
        )
        self._embeddings = HuggingFaceEmbeddings(model_name=config.embed_model)

    def evaluate(self, test_data: dict) -> pd.DataFrame:
        dataset = Dataset.from_dict(test_data)
        run_config = RunConfig(
            timeout=self._config.ragas_timeout,
            max_workers=self._config.ragas_max_workers,
        )
        result = evaluate(
            dataset,
            metrics=_METRICS,
            llm=self._evaluator_llm,
            embeddings=self._embeddings,
            run_config=run_config,
        )
        return result.to_pandas()
