"""Evaluation orchestrator — wires sources, populator, evaluator, and sinks together.

Depends only on abstractions (``EvalDatasetSource``, ``ResultSink``) and the concrete
``RagasEvaluator`` / ``LivePipelinePopulator``, all injected via the constructor
(Dependency Inversion). Holds no configuration logic of its own.
"""
from __future__ import annotations

from typing import Optional, Sequence

from cora_rc_ai.evaluation.config import EvalConfig
from cora_rc_ai.evaluation.data_sources import EvalDatasetSource
from cora_rc_ai.evaluation.evaluator import RagasEvaluator
from cora_rc_ai.evaluation.live_pipeline import LivePipelinePopulator
from cora_rc_ai.evaluation.reporters import ResultSink


class EvaluationOrchestrator:
    def __init__(
        self,
        config: EvalConfig,
        source: EvalDatasetSource,
        evaluator: RagasEvaluator,
        sinks: Sequence[ResultSink],
        populator: Optional[LivePipelinePopulator] = None,
    ):
        self._config = config
        self._source = source
        self._evaluator = evaluator
        self._sinks = sinks
        self._populator = populator

    async def run(self) -> None:
        print("Starting CORA RAGAS Evaluation...")
        test_data = self._source.load()

        if self._config.live_eval and self._populator is not None:
            print("LIVE_EVAL enabled — querying the real retriever + compliance agent...")
            test_data = await self._populator.populate(test_data)
        else:
            print(
                "LIVE_EVAL disabled — scoring static gold contexts/answers. "
                "Set LIVE_EVAL=true to evaluate the real pipeline."
            )

        df = self._evaluator.evaluate(test_data)

        for sink in self._sinks:
            sink.emit(df)

        print("Evaluation complete.")
