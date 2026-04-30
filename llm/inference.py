# llm/inference.py
import json
import time
import requests  # We are swapping urllib out for requests
import config

def run_llm(query: str, context: str) -> str:
    """
    Call Ollama API with fallback to mock response
    """
    prompt = f"""Context: {context}\n\nQuestion: {query}\n\nAnswer:"""
    
    try:
        return _call_ollama(prompt)
    except Exception as e:
        if config.USE_OLLAMA_FALLBACK:
            print(f"⚠ [LLM] Ollama unavailable ({str(e)[:50]}), using fallback")
            return _mock_llm_response(query, context)
        else:
            raise

def _call_ollama(prompt: str) -> str:
    """Call the llama.cpp server using the requests library"""
    payload = {
        "prompt": prompt,
        "stream": False,
        "n_predict": 256
    }
    
    try:
        # requests.post directly handles the networking and bypasses urllib quirks
        response = requests.post(
            f"{config.OLLAMA_HOST}/completion",
            json=payload,
            timeout=config.OLLAMA_TIMEOUT
        )
        response.raise_for_status() # Catches any 404 or 500 errors
        
        result = response.json()
        return result.get("content", "No response from LLM").strip()
        
    except Exception as e:
        raise Exception(f"LLM connection failed: {e}")

def _mock_llm_response(query: str, context: str) -> str:
    """Generate mock LLM response"""
    context_preview = context[:100].replace('\n', ' ')
    return f"[MOCK RESPONSE] Based on the context about '{context_preview}...', the answer to '{query}' is that this is a simulated response for testing purposes."