"""
Document ingestion and FAISS index building
"""
import os
import json
import numpy as np
from typing import List, Dict, Tuple

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠ faiss-cpu not installed. Install with: pip install faiss-cpu")

from rag.embedding_pipeline import EmbeddingPipeline

class DocumentIngester:
    def __init__(self, embedding_pipeline: EmbeddingPipeline):
        """Initialize with embedding pipeline"""
        if not FAISS_AVAILABLE:
            raise ImportError("faiss-cpu required for vector DB")
        
        self.embedder = embedding_pipeline
        self.documents: List[str] = []
        self.index = None
        self.dimension = embedding_pipeline.embedding_dim
    
    def ingest_text_file(self, filepath: str, chunk_size: int = 200):
        """
        Read text file and chunk it
        chunk_size: approximate characters per chunk
        """
        print(f"[DocumentIngester] Loading {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Simple chunking by character count
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        self.documents.extend(chunks)
        print(f"[DocumentIngester] Ingested {len(chunks)} chunks from {filepath}")
    
    def ingest_json_qa(self, filepath: str):
        """
        Load Q&A pairs from JSON file
        Expected format: [{"question": "...", "answer": "..."}, ...]
        """
        print(f"[DocumentIngester] Loading Q&A from {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            qa_pairs = json.load(f)
        
        for pair in qa_pairs:
            doc = f"Q: {pair.get('question', '')}\nA: {pair.get('answer', '')}"
            self.documents.append(doc)
        
        print(f"[DocumentIngester] Ingested {len(qa_pairs)} Q&A pairs")
    
    def build_index(self):
        """Build FAISS index from documents"""
        if not self.documents:
            print("⚠ No documents to index!")
            return
        
        print(f"[DocumentIngester] Embedding {len(self.documents)} documents...")
        embeddings = self.embedder.embed_batch(self.documents)
        embeddings = embeddings.astype(np.float32)
        
        print(f"[DocumentIngester] Building FAISS index...")
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings)
        print(f"[DocumentIngester] Index built with {self.index.ntotal} documents")
    
    def search(self, query: str, k: int = 3) -> List[Tuple[str, float]]:
        """
        Search for top-k most similar documents
        Returns: [(document, distance), ...]
        """
        if self.index is None:
            print("⚠ Index not built! Call build_index() first.")
            return []
        
        query_embedding = self.embedder.embed_text(query).astype(np.float32).reshape(1, -1)
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.documents):
                results.append((self.documents[idx], float(distance)))
        
        return results
    
    def save_index(self, index_path: str, docs_path: str):
        """Save index and documents to disk"""
        faiss.write_index(self.index, index_path)
        with open(docs_path, 'w') as f:
            json.dump(self.documents, f)
        print(f"[DocumentIngester] Saved index to {index_path}")
        print(f"[DocumentIngester] Saved documents to {docs_path}")
    
    def load_index(self, index_path: str, docs_path: str):
        """Load index and documents from disk"""
        self.index = faiss.read_index(index_path)
        with open(docs_path, 'r') as f:
            self.documents = json.load(f)
        print(f"[DocumentIngester] Loaded index from {index_path}")
        print(f"[DocumentIngester] Loaded {len(self.documents)} documents")