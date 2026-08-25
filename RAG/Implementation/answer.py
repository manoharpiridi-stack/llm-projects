import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from openai import OpenAI

from .ingest import ensure_vectorstore

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

MODELS = {
    "Groq · GPT-OSS 120B": ("groq", "openai/gpt-oss-120b"),
    "Groq · GPT-OSS 20B": ("groq", "openai/gpt-oss-20b"),
    "OpenRouter · GPT-4o mini": ("openrouter", "openai/gpt-4o-mini"),
}
DEFAULT_MODEL = "Groq · GPT-OSS 120B"
RETRIEVAL_K = 8

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company Insurellm.
You are chatting with a user about Insurellm.
If relevant, use the given context to answer any question.
If you don't know the answer, say so.
Keep answers grounded in the context. Do not invent employees, products, prices, or contracts.

Context:
{context}
"""


def get_client(provider):
    if provider == "groq":
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise RuntimeError("GROQ_API_KEY is missing from the .env file.")
        return OpenAI(
            api_key=groq_key.strip(),
            base_url="https://api.groq.com/openai/v1",
        )

    if provider == "openrouter":
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY is missing from the .env file.")
        return OpenAI(
            api_key=openrouter_key.strip(),
            base_url="https://openrouter.ai/api/v1",
        )

    raise RuntimeError(f"Unknown provider: {provider}")


def fetch_context(question: str) -> list[Document]:
    store = ensure_vectorstore()
    return store.similarity_search(question, k=RETRIEVAL_K)


def combined_question(question: str, history: list[dict] | None = None) -> str:
    history = history or []
    prior = "\n".join(m["content"] for m in history if m.get("role") == "user")
    return (prior + "\n" + question).strip()


def answer_question(
    question: str,
    history: list[dict] | None = None,
    client=None,
    model: str | None = None,
) -> tuple[str, list[Document]]:
    history = history or []
    if client is None or model is None:
        provider, model = MODELS[DEFAULT_MODEL]
        client = get_client(provider)

    docs = fetch_context(combined_question(question, history))
    context = "\n\n".join(doc.page_content for doc in docs)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        *[
            {"role": item["role"], "content": item["content"]}
            for item in history
            if item.get("role") in {"user", "assistant"}
        ],
        {"role": "user", "content": question},
    ]
    response = client.chat.completions.create(model=model, messages=messages)
    return (response.choices[0].message.content or "").strip(), docs
