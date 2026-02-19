import os
from typing import Any, Dict, List, Tuple

import httpx

class LLMError(Exception):
    pass

def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "openai").strip().lower()

def _openai_cfg() -> Tuple[str, str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY environment variable is not set.")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return api_key, base_url.rstrip("/") + "/", model

def _nebius_cfg() -> Tuple[str, str, str]:
    api_key = os.getenv("NEBIUS_API_KEY")
    if not api_key:
        raise LLMError("NEBIUS_API_KEY environment variable is not set.")
    base_url = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
    model = os.getenv("NEBIUS_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct-fast")
    return api_key, base_url.rstrip("/") + "/", model

async def chat_completion(messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
    provider = _provider()

    if provider == "openai":
        api_key, base_url, model = _openai_cfg()
    elif provider == "nebius":
        api_key, base_url, model = _nebius_cfg()
    else:
        raise LLMError('LLM_PROVIDER must be "openai" or "nebius".')

    url = base_url + "chat/completions"

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    # OpenAI supports JSON mode via response_format on Chat Completions
    if provider == "openai":
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload, timeout=90.0)

    if r.status_code >= 400:
        raise LLMError(f"{provider} API error ({r.status_code}): {r.text[:500]}")

    data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise LLMError("Unexpected LLM response format.") from e
