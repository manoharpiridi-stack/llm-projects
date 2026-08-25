---
title: FlightAI Assistant
emoji: ✈️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.47.2
app_file: app.py
pinned: false
---

# Project 2: FlightAI Assistant

Gradio chat assistant from the Week 2 Day 4–5 airline lab. It answers as FlightAI and looks up sample ticket prices with a tool call.

## What it does

1. Chat with a short, courteous FlightAI system prompt.
2. When you ask for a fare, the model calls `get_ticket_price`.
3. The app looks up a hardcoded city and sends the price back so the model can reply in one sentence.

Sample return fares: London $799, Paris $899, Tokyo $1400, Berlin $499.

## Files

| File | Role |
|------|------|
| `app.py` | Client, tool, chat loop, Gradio UI |
| `requirements.txt` | Hugging Face Spaces / pip install |

## Setup

From `LLM Projects`:

```powershell
uv sync
```

Keys live in the parent `.env` (same file as Project 1):

```env
GROQ_API_KEY=your_groq_key
```

If Groq is missing, the app uses `OPENROUTER_API_KEY`. Optional: `FLIGHT_MODEL` to override the default (`llama-3.3-70b-versatile` on Groq).

## Run locally

```powershell
uv run python "Project_2/app.py"
```

Open the URL Gradio prints (usually `http://127.0.0.1:7860`).

## Deploy to Hugging Face Spaces

1. Create a **Gradio** Space.
2. Upload `app.py`, `requirements.txt`, and this `README.md`.
3. In Space **Settings → Secrets**, add `GROQ_API_KEY` (or `OPENROUTER_API_KEY`).
4. The Space builds from `requirements.txt` and runs `app.py`.
