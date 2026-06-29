"""CORA RAGAS evaluation entrypoint.

Thin composition root: builds the configured pieces and runs the orchestrator. All real
work lives in the ``cora_rc_ai.evaluation`` package modules (config, data_sources,
live_pipeline, evaluator, reporters, orchestrator).

Run from the repo root:

    python -c "from dotenv import load_dotenv; load_dotenv('cora_rc_ai/.env'); \
import runpy; runpy.run_path('cora_rc_ai/evaluation/ragas_eval.py', run_name='__main__')"

Set LIVE_EVAL=true to score the real retriever + compliance agent instead of static gold.
"""
import asyncio
from typing import Optional

from cora_rc_ai.evaluation.config import EvalConfig
from cora_rc_ai.evaluation.data_sources import resolve_dataset_source
from cora_rc_ai.evaluation.evaluator import RagasEvaluator
from cora_rc_ai.evaluation.live_pipeline import LivePipelinePopulator
from cora_rc_ai.evaluation.orchestrator import EvaluationOrchestrator
from cora_rc_ai.evaluation.reporters import (
    ConsoleReporter,
    CsvResultWriter,
    LangSmithResultSink,
)


def build_orchestrator(config: Optional[EvalConfig] = None) -> EvaluationOrchestrator:
    config = config or EvalConfig.from_env()

    source = resolve_dataset_source(config)
    evaluator = RagasEvaluator(config)

    sinks = [CsvResultWriter(config.results_path), ConsoleReporter()]
    #if config.enable_langsmith_logging:
     #   sinks.append(LangSmithResultSink(config))
    #else:
    #    print(
    #        "\nLangSmith logging disabled — set ENABLE_LANGSMITH_LOGGING=true with a valid key."
    #    )

    populator = LivePipelinePopulator(config) if config.live_eval else None
    return EvaluationOrchestrator(config, source, evaluator, sinks, populator)


async def run_evaluation() -> None:
    await build_orchestrator().run()


if __name__ == "__main__":
    asyncio.run(run_evaluation())
