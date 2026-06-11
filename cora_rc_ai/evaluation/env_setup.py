"""Import-time environment hardening.

Importing this module (with no heavy dependencies) sets the environment variables
that MUST be in place *before* ragas / langchain / transformers are imported:

- Disable LangChain/LangSmith background tracing. The configured hosted key returns
  403 and auto-tracing would otherwise flood every LLM call with ingest errors.
- Force HuggingFace/transformers offline so the already-cached embeddings model is
  used instead of repeatedly retrying downloads (which crashes when offline).
- Provide a placeholder GOOGLE_API_KEY so ADK does not probe Google metadata when the
  live compliance agent runs against a local Ollama model.

``setdefault`` is used for the offline/Google keys so any value already provided by the
user or ``.env`` wins.
"""
import os

# Tracing is force-disabled (not setdefault) — .env ships LANGSMITH_TRACING=true.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("GOOGLE_API_KEY", "local-ollama-no-google-api")
