# llm/inference. py
"""
LLM Inference with Ollama + Fallback
"""
import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import config

def run_llm(query: str, context: str) -> str:
    """
    Call Ollama API with fallback to mock response
    """
    prompt = f"""Context: {context}

Question: {query}

Answer:"""
    
    try:
        return _call_ollama(prompt)
    except Exception as e:
        if config.USE_OLLAMA_FALLBACK:
            print(f"⚠ [LLM] Ollama unavailable ({str(e)[:50]}), using fallback")
            return _mock_llm_response(query, context)
        else:
            raise

def _call_ollama(prompt: str) -> str:
    """Call real Ollama API"""
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    req = Request(
        f"{config.OLLAMA_HOST}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urlopen(req, timeout=config.OLLAMA_TIMEOUT) as response:
            result = json.loads(response.read().decode())
            return result.get("response", "No response from Ollama")
    except (URLError, HTTPError, TimeoutError) as e:
        raise Exception(f"Ollama connection failed: {e}")

def _mock_llm_response(query: str, context: str) -> str:
    """
    Generate mock LLM response (for testing without Ollama)
    """
    context_preview = context[:100].replace('\n', ' ')
    return f"[MOCK RESPONSE] Based on the context about '{context_preview}...', the answer to '{query}' is that this is a simulated response for testing purposes."