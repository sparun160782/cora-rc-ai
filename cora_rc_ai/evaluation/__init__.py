"""CORA RAGAS evaluation package.

A small, SOLID-structured evaluation framework around RAGAS:

- ``env_setup``    : import-time environment hardening (tracing off, offline models).
- ``config``       : single source of runtime configuration (``EvalConfig``).
- ``sample_data``  : built-in fallback gold dataset.
- ``data_sources`` : pluggable dataset loaders (``EvalDatasetSource``).
- ``live_pipeline``: populate contexts/answers from the real retriever + agent.
- ``evaluator``    : RAGAS scoring (``RagasEvaluator``).
- ``reporters``    : pluggable result sinks (``ResultSink``).
- ``orchestrator`` : wires the pieces together (``EvaluationOrchestrator``).
"""
