#rag/embedding_pipeline.py
import numpy as np
from typing import List
from fastembed import TextEmbedding

class EmbeddingPipeline:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize with fastembed (ONNX runtime, PyTorch-free)"""
        self.model_name = model_name
        self.embedding_dim = 384
        
        print(f"[EmbeddingPipeline] Loading ONNX embedding model: {self.model_name}")
        # Initialize the lightweight embedding model
        self.model = TextEmbedding(model_name=self.model_name)
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate real semantic embedding from text"""
        # fastembed returns a generator, so we convert it to a list and grab the first array
        embedding = list(self.model.embed([text]))[0]
        return embedding.astype(np.float32)
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Embed multiple texts efficiently"""
        embeddings = list(self.model.embed(texts))
        return np.array(embeddings, dtype=np.float32)