from __future__ import annotations

import os

from car_hunter.config import GEMINI_MODEL, GROQ_MODEL, LLM_PROVIDER, OLLAMA_MODEL


class LLMUnavailable(RuntimeError):
    pass


def complete(prompt: str, system: str | None = None) -> str:
    provider = LLM_PROVIDER
    if provider == "ollama":
        return _ollama(prompt, system)
    if provider == "groq":
        return _groq(prompt, system)
    if provider == "gemini":
        return _gemini(prompt, system)
    if provider in {"none", "off"}:
        raise LLMUnavailable("LLM_PROVIDER is off")
    raise LLMUnavailable(f"Unknown LLM_PROVIDER={provider}")


def available() -> bool:
    try:
        if LLM_PROVIDER == "ollama":
            import ollama

            ollama.list()
            return True
        if LLM_PROVIDER == "groq":
            return bool(os.getenv("GROQ_API_KEY"))
        if LLM_PROVIDER == "gemini":
            return bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        return False
    except Exception:
        return False


def _ollama(prompt: str, system: str | None) -> str:
    import ollama

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
    return response["message"]["content"]


def _groq(prompt: str, system: str | None) -> str:
    from groq import Groq

    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise LLMUnavailable("GROQ_API_KEY is not set")
    client = Groq(api_key=key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(model=GROQ_MODEL, messages=messages)
    return response.choices[0].message.content or ""


def _gemini(prompt: str, system: str | None) -> str:
    from google import genai

    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise LLMUnavailable("GOOGLE_API_KEY is not set")
    client = genai.Client(api_key=key)
    full = f"{system}\n\n{prompt}" if system else prompt
    response = client.models.generate_content(model=GEMINI_MODEL, contents=full)
    return response.text or ""
