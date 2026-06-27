import logging
import os

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
SUMMARIZER_ENABLED = os.getenv("SUMMARIZER_ENABLED", "true").lower() == "true"

PROMPT_TEMPLATE = (
    "Summarize this AI/ML article in 3-5 sentences for a technical audience:\n\n{text}"
)


async def summarize(text: str) -> str:
    """Generate a summary for the given text using Ollama. Returns empty string on error."""
    if not SUMMARIZER_ENABLED:
        return ""
    if not text or not text.strip():
        return ""

    prompt = PROMPT_TEMPLATE.format(text=text)
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
    except Exception as exc:
        logger.warning("Ollama summarization failed: %s", exc)
        return ""
