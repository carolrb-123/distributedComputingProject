#rag/retriever.py
"""
RAG Retriever - Enhanced with FAISS
"""
from rag.document_ingester import DocumentIngester
from typing import Optional

_ingester: Optional[DocumentIngester] = None

def initialize_retriever(ingester: DocumentIngester):
    """Initialize global retriever with document ingester"""
    global _ingester
    _ingester = ingester

def retrieve_context(query: str, k: int = 3) -> str:
    """
    Retrieve relevant context from FAISS index
    Returns concatenated documents as context string
    """
    if _ingester is None:
        return "[RETRIEVAL FAILED] Ingester not initialized"
    
    results = _ingester.search(query, k=k)
    
    if not results:
        return "[NO CONTEXT FOUND]"
    
    # Concatenate top results
    context = "\n---\n".join([doc for doc, _ in results])
    return context