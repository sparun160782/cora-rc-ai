import os
import logging
from typing import List

# Force HuggingFace to use the local cache only — avoids blocked network HEAD
# requests behind a corporate proxy (SSL: CERTIFICATE_VERIFY_FAILED).
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# Prevent PyTorch from enumerating CUDA/GPU drivers at startup on Windows.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

# NOTE: sentence_transformers (and hence torch) is NOT imported here at module
# level — it is lazy-loaded inside __init__ to keep startup fast and prevent
# CUDA driver enumeration from hanging or crashing the process on Windows.

logger = logging.getLogger(__name__)

class EmbeddingsModel:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EmbeddingsModel, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = None):
        if self._initialized:
            return
        if model_name is None:
            model_name = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-large-en-v1.5")
        logger.info(f"Loading embedding model: {model_name}...")
        from sentence_transformers import SentenceTransformer  # lazy import — keeps torch out of startup
        self.model = SentenceTransformer(model_name)
        self._initialized = True

    def get_embedding(self, text: str) -> List[float]:
        # Generate embedding as a float list
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
