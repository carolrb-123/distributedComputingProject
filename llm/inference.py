import requests
import config
import threading

# 🔒 prevents overload of single llama.cpp server
LLM_LOCK = threading.Lock()


def run_llm(query: str, context: str) -> str:
    prompt = f"""Context: {context}

Question: {query}

Answer:"""

    try:
        return _call_llamacpp(prompt)
    except Exception as e:
        print(f"❌ [LLM ERROR] {e}")
        raise


def _call_llamacpp(prompt: str) -> str:
    with LLM_LOCK:  # 🔥 CRITICAL FIX

        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "n_predict": 16
        }

        response = requests.post(
            f"{config.LLM_SERVER_URL}/v1/chat/completions",
            json=payload,
            timeout=config.LLM_TIMEOUT
        )

        response.raise_for_status()
        result = response.json()

        # DEBUG (optional)
        #print("LLM RESPONSE:", result)

        try:
            return result["choices"][0]["message"]["content"].strip()
        except Exception:
            print("BAD LLM RESPONSE:", result)
            raise