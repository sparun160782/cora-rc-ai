import os
import logging
from typing import List, Dict, Any

# Force HuggingFace offline BEFORE any transformers import fires — avoids
# network HEAD requests that hang behind a corporate proxy.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
# Force CPU-only device discovery to prevent PyTorch hanging on Windows
# while enumerating CUDA/GPU drivers at startup.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

# EmbeddingsModel and PgVectorAdapter are NOT imported at module level — they
# pull in sentence_transformers/torch (slow + can crash at startup on Windows).
# They are lazy-imported inside HybridRetriever.__init__ instead.

logger = logging.getLogger(__name__)

class BGEReranker:
    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = os.getenv("RERANKER_MODEL_NAME", "BAAI/bge-reranker-large")
        self.available = False
        self.tokenizer = None
        self.model = None
        self.device = "cpu"
        try:
            # Lazy-import torch and transformers — keeps them out of the module-level
            # import so they only load when BGEReranker is actually instantiated.
            import torch  # noqa: PLC0415
            from transformers import AutoTokenizer, AutoModelForSequenceClassification  # noqa: PLC0415

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading reranker model: {model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(self.device)
            self.model.eval()
            self.available = True
            self._torch = torch  # hold reference for use in score()
        except Exception as e:
            # Model not cached / network blocked. Degrade gracefully: retrieval
            # continues using the upstream hybrid-search scores without reranking.
            logger.warning(
                f"Reranker unavailable ({e}); falling back to hybrid-search order without reranking."
            )
            self._torch = None

    def score(self, query: str, documents: List[str]) -> List[float]:
        if not documents:
            return []
        if not self.available or self._torch is None:
            # Passthrough: preserve existing candidate order.
            return [0.0] * len(documents)
        torch = self._torch
        pairs = [[query, doc] for doc in documents]
        with torch.no_grad():
            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors="pt",
                max_length=512,
            ).to(self.device)
            logits = self.model(**inputs).logits.view(-1).float()
            return logits.tolist()

class HybridRetriever:
    def __init__(self):
        # Lazy imports — keeps sentence_transformers/torch out of module-level
        # execution to prevent CUDA hang/crash at server startup on Windows.
        from cora_rc_ai.backend_agentic.models.embeddings_model import EmbeddingsModel
        from cora_rc_ai.data_layer.vector_store.pgvector_adapter import PgVectorAdapter
        self.embeddings_model = EmbeddingsModel()
        self.db_adapter = PgVectorAdapter()
        # Initialize reranker lazily or on startup
        self.reranker = BGEReranker()

    def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        logger.info(f"RAG retrieving for query: {query}")
        
        # 1. Generate query embedding
        query_vector = self.embeddings_model.get_embedding(query)
        
        # 2. Database Hybrid Search with RRF (returns combined top 30 chunks)
        candidate_chunks = self.db_adapter.hybrid_search(
            query_text=query,
            query_vector=query_vector,
            limit=20
        )
        
        if not candidate_chunks:
            logger.warning("No candidate chunks found in RAG database.")
            return []

        # 3. Extract text for re-ranking
        chunk_texts = [c['chunk_text'] for c in candidate_chunks]
        
        # 4. Score candidates using Cross-Encoder Reranker
        rerank_scores = self.reranker.score(query, chunk_texts)
        
        # Assign scores to candidates
        for idx, score in enumerate(rerank_scores):
            candidate_chunks[idx]['rerank_score'] = score
            
        # 5. Sort candidates by re-ranker score (descending)
        sorted_candidates = sorted(candidate_chunks, key=lambda x: x['rerank_score'], reverse=True)
        
        # 6. Context Compression & Deduplication
        compressed_results = []
        seen_texts = set()
        
        for candidate in sorted_candidates:
            text_normalized = " ".join(candidate['chunk_text'].lower().split())
            if text_normalized in seen_texts:
                continue
            seen_texts.add(text_normalized)
            
            # Additional cleanup of duplicate headers/footers
            compressed_results.append(candidate)
            if len(compressed_results) >= limit:
                break
                
        logger.info(f"Retrieved {len(compressed_results)} compressed chunks.")
        return compressed_results
