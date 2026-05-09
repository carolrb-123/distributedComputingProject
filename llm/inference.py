#llm/inference.py
import requests
import config
import time


def run_llm(query: str, context: str, server_url: str, session=None) -> str:
    prompt = f"""Context: {context}

Question: {query}

Answer:"""

    try:
        return _call_llamacpp(prompt, server_url, session)
    except Exception as e:
        print(f"❌ [LLM ERROR] {e}")
        raise


def _call_llamacpp(prompt: str, server_url: str, session=None) -> str:
    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens": config.LLM_MAX_TOKENS,
    }

    client = session if session else requests  

    for attempt in range(2):
        try:
            response = client.post(
                f"{server_url}/v1/chat/completions",
                json=payload,
                timeout=config.LLM_TIMEOUT
            )
            response.raise_for_status()
            break
        except Exception as e:
            if attempt == 1:
                raise
            time.sleep(0.2)

    response.raise_for_status()
    result = response.json()

    print(f"DEBUG: calling llama at {server_url}")

    return result["choices"][0]["message"]["content"].strip()
