#rag/embedding_pipeline.py
"""
Lightweight embedding pipeline (mock - avoids torch segfault on Intel Mac)
"""
import numpy as np
from typing import List
import hashlib

class EmbeddingPipeline:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize with mock embeddings (no torch load)"""
        self.model_name = model_name
        self.embedding_dim = 384  # Standard dimension
        print(f"[EmbeddingPipeline] Mock mode (avoiding torch segfault on Intel Mac)")
        print(f"[EmbeddingPipeline] Embedding dim: {self.embedding_dim}")
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate deterministic mock embedding from text hash"""
        # Create reproducible embedding from text hash
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert hash to embedding
        embedding = np.frombuffer(hash_bytes, dtype=np.float32)
        # Pad/truncate to embedding_dim
        if len(embedding) < self.embedding_dim:
            embedding = np.pad(embedding, (0, self.embedding_dim - len(embedding)))
        else:
            embedding = embedding[:self.embedding_dim]
        
        # Normalize
        return embedding / (np.linalg.norm(embedding) + 1e-9)
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Embed multiple texts"""
        embeddings = np.array([self.embed_text(text) for text in texts], dtype=np.float32)
        return embeddings
    
    def embed_and_normalize(self, text: str) -> np.ndarray:
        """Embed and normalize to unit vector"""
        embedding = self.embed_text(text)
        return embedding / (np.linalg.norm(embedding) + 1e-9)