"""Pluggable evaluation dataset sources (Open/Closed + Dependency Inversion).

Consumers depend on the ``EvalDatasetSource`` abstraction; new sources (CSV, database,
HTTP, ...) can be added without touching the orchestrator. ``resolve_dataset_source``
picks the right concrete source from ``EvalConfig``.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from cora_rc_ai.evaluation.config import EvalConfig
from cora_rc_ai.evaluation.sample_data import FALLBACK_TEST_DATA

REQUIRED_FIELDS = {"question", "answer", "contexts", "ground_truth"}


class EvalDatasetSource(ABC):
    """Abstraction for anything that can produce a RAGAS-shaped dataset dict."""

    @abstractmethod
    def load(self) -> dict:
        """Return a dict with at least the REQUIRED_FIELDS keys."""
        raise NotImplementedError


class FallbackDatasetSource(EvalDatasetSource):
    """Returns the built-in RBI compliance gold dataset."""

    def load(self) -> dict:
        return dict(FALLBACK_TEST_DATA)


class JsonFileDatasetSource(EvalDatasetSource):
    """Loads and validates a JSON evalset from disk."""

    def __init__(self, path: Path):
        self._path = path

    def load(self) -> dict:
        with self._path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ValueError(f"Evalset missing required fields: {sorted(missing)}")
        return data


def resolve_dataset_source(config: EvalConfig) -> EvalDatasetSource:
    """Select a dataset source based on configuration.

    Falls back to the built-in sample when no path is configured or the file is missing
    / has an unsupported extension.
    """
    if not config.evalset_path:
        return FallbackDatasetSource()

    path = Path(config.evalset_path)
    if not path.exists():
        print(f"Evalset not found at {path}. Using fallback sample.")
        return FallbackDatasetSource()

    if path.suffix.lower() == ".json":
        return JsonFileDatasetSource(path)

    print("Unsupported evalset format (use JSON). Using fallback sample.")
    return FallbackDatasetSource()
