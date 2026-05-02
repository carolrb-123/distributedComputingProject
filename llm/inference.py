import requests
import config
import threading

# 🔒 prevents overload of single llama.cpp server
LLM_LOCK = threading.Lock()


def run_llm(query: str, context: str, server_url: str) -> str:
    prompt = f"""Context: {context}

Question: {query}

Answer:"""

    try:
        return _call_llamacpp(prompt, server_url)
    except Exception as e:
        print(f"❌ [LLM ERROR] {e}")
        raise


def _call_llamacpp(prompt: str, server_url: str) -> str:
    payload = {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "n_predict": 32
    }

    response = requests.post(
        f"{server_url}/v1/chat/completions",
        json=payload,
        timeout=config.LLM_TIMEOUT
    )

    response.raise_for_status()
    result = response.json()
    print(f"DEBUG: calling llama at {server_url}")
    return result["choices"][0]["message"]["content"].strip()