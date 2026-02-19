import os
from typing import Any, Dict, List, Optional

import httpx


class NebiusError(Exception):
    pass


def get_nebius_config() -> tuple[str, str]:
    api_key = os.getenv("NEBIUS_API_KEY")
    if not api_key:
        raise NebiusError("NEBIUS_API_KEY environment variable is not set.")
    base_url = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
    model = os.getenv("NEBIUS_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct-fast")
    return api_key, base_url.rstrip("/") + "/", model


async def chat_completion(messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
    api_key, base_url, model = get_nebius_config()
    url = base_url + "chat/completions"

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload, timeout=60.0)

    if r.status_code >= 400:
        # Return a readable error message (don’t leak key).
        raise NebiusError(f"Nebius API error ({r.status_code}): {r.text[:500]}")

    data = r.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise NebiusError("Unexpected Nebius response format.") from e