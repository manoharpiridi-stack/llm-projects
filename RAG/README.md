---
title: Insurellm RAG Assistant
emoji: 🏢
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.47.2
app_file: app.py
pinned: false
---

# Project 5: Insurellm RAG Assistant

Gradio chatbot over the Insurellm knowledge base. Greetings stay as chat. Real questions use the pro RAG path: LLM chunking, query rewrite, dual retrieve, and rerank.

## What it does

1. If the message is small talk (`hi`, `thanks`, `bye`, …), it answers as a chatbot and **does not** search the knowledge base.
2. If the message needs a fact, it rewrites the query from chat history, retrieves, reranks, and answers from those passages.
3. The right-hand panel shows retrieved context only when a lookup ran.

`evaluator.py` scores retrieval and answers on `Evaluation/tests.jsonl`.

## Files

| File | Role |
|------|------|
| `app.py` | Chat UI, model dropdown, retrieved-context panel |
| `evaluator.py` | Evaluation dashboard |
| `Pro_Implementation/ingest.py` | LLM chunking + embeddings into `preprocessed_db` |
| `Pro_Implementation/answer.py` | Chat vs retrieve, rewrite, rerank, answer |
| `Evaluation/eval.py` | Retrieval math and answer judging |
| `knowledge-base/` | Source documents |

## Setup

From `LLM Projects`:

```powershell
uv sync
uv run python Project_5/Pro_Implementation/ingest.py
```

Ingest calls Groq once per markdown file and can take a while. Embeddings are local MiniLM (no OpenAI key). Chat, chunking, rewrite, and rerank use Groq.

```env
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key
```

## Run locally

```powershell
uv run python Project_5/app.py
uv run python Project_5/evaluator.py
```
