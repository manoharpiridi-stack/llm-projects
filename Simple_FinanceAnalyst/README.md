---
title: Financial Analysis Agent
emoji: 📈
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 5.47.2
app_file: app.py
pinned: false
---

# Project 6: Financial Analysis Agent

A beginner-friendly **Agno** agent (Agno used to be called **Phidata**).
You ask about a stock. The LLM calls Yahoo Finance tools, then answers with real numbers.

## How to read the code

There are only two important files.

### `agent.py` — the brain

1. Load `GROQ_API_KEY` from `.env`.
2. Create `YFinanceTools` so the model can fetch live market data.
3. Create an `Agent` with a Groq model, those tools, and short instructions.
4. `ask(question)` runs one question and returns the text answer.

Agno handles the tool loop: the model may call `get_current_stock_price`, get `310.34` back, then write a sentence.

### `app.py` — the chat UI

`chat()` receives the user's message and returns `ask(message)`.
Gradio `ChatInterface` draws the chat box.

`finance_agent.py` is optional: same agent, printed in the terminal.

## Setup

From `LLM Projects`:

```powershell
uv sync
```

In the repo-root `.env`:

```env
GROQ_API_KEY=your_groq_key
```

## Run

```powershell
uv run python Project_6/app.py
```

Terminal demo:

```powershell
uv run python Project_6/finance_agent.py
```

## Try asking

- What is NVDA's current price?
- Summarize Apple fundamentals: P/E, margins, and revenue.
- How has MSFT performed recently?
