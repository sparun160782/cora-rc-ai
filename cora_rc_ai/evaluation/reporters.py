"""Result sinks — pluggable destinations for scored results (Interface Segregation + OCP).

Each sink implements the narrow ``ResultSink.emit`` interface and does exactly one thing:
write a CSV, print a console summary, or push to LangSmith. New destinations can be added
without modifying the orchestrator.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd

from cora_rc_ai.evaluation.config import METRIC_NAMES, EvalConfig


class ResultSink(ABC):
    """Consumes a scored RAGAS results DataFrame."""

    @abstractmethod
    def emit(self, df: pd.DataFrame) -> None:
        raise NotImplementedError


class CsvResultWriter(ResultSink):
    """Persists the full results DataFrame to CSV."""

    def __init__(self, path: Path):
        self._path = path

    def emit(self, df: pd.DataFrame) -> None:
        df.to_csv(self._path, index=False)
        print(f"Saved full results to {self._path}")


class ConsoleReporter(ResultSink):
    """Prints a per-row metric table plus mean scores to stdout.

    RAGAS >=0.2 renames columns (question->user_input, answer->response,
    ground_truth->reference); only columns present in the frame are displayed.
    """

    def emit(self, df: pd.DataFrame) -> None:
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 250)
        pd.set_option("display.max_colwidth", 60)

        metric_cols = list(METRIC_NAMES)
        present_metrics = [c for c in metric_cols if c in df.columns]

        print("\n=== Evaluation Results ===")
        display_cols = [c for c in (["user_input"] + metric_cols) if c in df.columns]
        print(df[display_cols])

        if present_metrics:
            print("\n=== Mean Scores ===")
            print(df[present_metrics].mean().round(4).to_string())


class LangSmithResultSink(ResultSink):
    """Optional: logs each row + metric feedback to LangSmith.

    Off by default (the shipped key returns 403). Fails soft and stops after the first
    error to avoid flooding the console.
    """

    def __init__(self, config: EvalConfig):
        from langsmith import Client as LangSmithClient  # noqa: PLC0415

        self._config = config
        self._client = LangSmithClient(
            api_url=config.langsmith_endpoint,
            api_key=config.langsmith_api_key,
        )

    def emit(self, df: pd.DataFrame) -> None:
        project = self._config.langsmith_project
        present_metrics = [c for c in METRIC_NAMES if c in df.columns]
        print("\nLogging results to LangSmith...")
        for _, row in df.iterrows():
            try:
                run_id = uuid4()
                self._client.create_run(
                    id=run_id,
                    name="CORA RAG Evaluation",
                    run_type="chain",
                    inputs={"question": row.get("user_input")},
                    project_name=project,
                    start_time=datetime.now(tz=timezone.utc),
                )
                self._client.update_run(
                    run_id=run_id,
                    outputs={
                        "answer": row.get("response"),
                        "ground_truth": row.get("reference"),
                    },
                    end_time=datetime.now(tz=timezone.utc),
                )
                for metric in present_metrics:
                    self._client.create_feedback(
                        run_id=run_id,
                        key=metric,
                        score=float(row[metric]),
                        source_info={"evaluator": "ragas"},
                    )
            except Exception as exc:  # noqa: BLE001
                print(f"Warning: stopping LangSmith logging after error: {exc}")
                break
        print("LangSmith logging done for project:", project)
