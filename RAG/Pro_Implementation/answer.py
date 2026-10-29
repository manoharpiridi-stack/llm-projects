import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from tenacity import retry, wait_exponential

from .ingest import (
    Result,
    collection_ready,
    embed_query,
    get_collection,
)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

MODELS = {
    "Groq · GPT-OSS 120B": ("groq", "openai/gpt-oss-120b"),
    "Groq · GPT-OSS 20B": ("groq", "openai/gpt-oss-20b"),
    "OpenRouter · GPT-4o mini": ("openrouter", "openai/gpt-4o-mini"),
}
DEFAULT_MODEL = "Groq · GPT-OSS 120B"
RETRIEVAL_K = 20
FINAL_K = 8
wait = wait_exponential(multiplier=1, min=10, max=240)

CHAT_SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing Insurellm.
You are chatting with a user. Keep replies short and natural.
If they greet you or make small talk, greet them back and invite questions about
Insurellm products, employees, or contracts.
Do not invent company facts. If you would need the knowledge base, say you can look that up.
"""

RAG_SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company Insurellm.
You are chatting with a user about Insurellm.
Use the given context to answer the question. Be accurate, relevant, and complete.
If the context does not contain the answer, say you don't know.
Do not invent employees, products, prices, or contracts.

Context:
{context}
"""

SMALLTALK = {
    "hi",
    "hello",
    "hey",
    "hiya",
    "yo",
    "hi there",
    "hello there",
    "hey there",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "how are you doing",
    "how's it going",
    "hows it going",
    "what's up",
    "whats up",
    "thanks",
    "thank you",
    "thx",
    "ty",
    "ok",
    "okay",
    "cool",
    "great",
    "nice",
    "bye",
    "goodbye",
    "see you",
    "cya",
}

QUESTION_HINTS = {
    "who",
    "what",
    "when",
    "where",
    "why",
    "which",
    "how",
    "price",
    "cost",
    "tier",
    "contract",
    "employee",
    "product",
    "salary",
    "insurellm",
}


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="Chunk ids from most relevant to least relevant, using the provided ids"
    )


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


def normalize_text(question: str) -> str:
    text = question.strip().lower()
    text = re.sub(r"[^\w\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_smalltalk(question: str) -> bool:
    text = normalize_text(question)
    if not text:
        return True
    if text in SMALLTALK:
        return True
    words = text.split()
    if len(words) <= 4 and words[0] in {"hi", "hello", "hey", "thanks", "thank"}:
        return not bool(QUESTION_HINTS.intersection(words))
    return False


def history_messages(history: list[dict] | None):
    history = history or []
    return [
        {"role": item["role"], "content": item["content"]}
        for item in history
        if item.get("role") in {"user", "assistant"}
    ]


def parse_json_model(raw: str, model_cls):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    try:
        return model_cls.model_validate_json(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise
        return model_cls.model_validate_json(text[start : end + 1])


@retry(wait=wait)
def rewrite_query(question, history, client, model):
    prompt = f"""
You are about to search a company knowledge base.

Conversation so far:
{history}

Current user message:
{question}

Rewrite this as one short, specific search query that is most likely to find the right passage.
If the message is small talk and not a knowledge question, reply with exactly: NONE
Respond ONLY with the search query, nothing else.
"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return (response.choices[0].message.content or "").strip()


def apply_rank(chunks, order):
    used = set()
    ranked = []
    for raw_id in order:
        idx = raw_id - 1 if raw_id >= 1 else raw_id
        if 0 <= idx < len(chunks) and idx not in used:
            ranked.append(chunks[idx])
            used.add(idx)
    for index, chunk in enumerate(chunks):
        if index not in used:
            ranked.append(chunk)
    return ranked


@retry(wait=wait)
def rerank(question, chunks, client, model):
    if len(chunks) <= 1:
        return chunks
    user_prompt = (
        f"The user asked:\n\n{question}\n\n"
        "Order all chunk ids by relevance, most relevant first. "
        "Reply with JSON {\"order\": [1, 2, ...]}. Include every chunk id.\n\n"
    )
    for index, chunk in enumerate(chunks):
        user_prompt += f"# CHUNK ID: {index + 1}:\n\n{chunk.page_content}\n\n"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a document re-ranker. Reply with JSON only.",
            },
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    try:
        order = parse_json_model(
            response.choices[0].message.content or "", RankOrder
        ).order
        return apply_rank(chunks, order)
    except Exception:
        return chunks


def fetch_context_unranked(question):
    if not collection_ready():
        raise RuntimeError(
            "The pro vector index is empty. Run: "
            "uv run python RAG/Pro_Implementation/ingest.py"
        )
    query = embed_query(question)
    results = get_collection().query(query_embeddings=[query], n_results=RETRIEVAL_K)
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    chunks = []
    for page, meta in zip(documents, metadatas):
        chunks.append(Result(page_content=page, metadata=meta or {}))
    return chunks


def merge_chunks(chunks, extra):
    merged = chunks[:]
    existing = {chunk.page_content for chunk in chunks}
    for chunk in extra:
        if chunk.page_content not in existing:
            merged.append(chunk)
            existing.add(chunk.page_content)
    return merged


def fetch_context(original_question, history=None, client=None, model=None):
    if client is None or model is None:
        provider, model = MODELS[DEFAULT_MODEL]
        client = get_client(provider)

    rewritten = rewrite_query(original_question, history or [], client, model)
    if rewritten.upper() == "NONE":
        return []

    chunks = fetch_context_unranked(original_question)
    if rewritten and rewritten.lower() != original_question.lower():
        chunks = merge_chunks(chunks, fetch_context_unranked(rewritten))
    reranked = rerank(original_question, chunks, client, model)
    return reranked[:FINAL_K]


def make_rag_messages(question, history, chunks):
    context = "\n\n".join(
        f"Extract from {chunk.metadata.get('source', 'unknown')}:\n{chunk.page_content}"
        for chunk in chunks
    )
    return (
        [{"role": "system", "content": RAG_SYSTEM_PROMPT.format(context=context)}]
        + history_messages(history)
        + [{"role": "user", "content": question}]
    )


def answer_question(
    question: str,
    history: list[dict] | None = None,
    client=None,
    model: str | None = None,
) -> tuple[str, list]:
    history = history or []
    if client is None or model is None:
        provider, model = MODELS[DEFAULT_MODEL]
        client = get_client(provider)

    if is_smalltalk(question):
        messages = (
            [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
            + history_messages(history)
            + [{"role": "user", "content": question}]
        )
        response = client.chat.completions.create(model=model, messages=messages)
        return (response.choices[0].message.content or "").strip(), []

    chunks = fetch_context(question, history, client=client, model=model)
    if not chunks:
        messages = (
            [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
            + history_messages(history)
            + [{"role": "user", "content": question}]
        )
        response = client.chat.completions.create(model=model, messages=messages)
        return (response.choices[0].message.content or "").strip(), []

    messages = make_rag_messages(question, history, chunks)
    response = client.chat.completions.create(model=model, messages=messages)
    return (response.choices[0].message.content or "").strip(), chunks
