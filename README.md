# LLM Projects

Course apps built with Gradio, Groq, and related LLM tools.

| Folder | Project |
|--------|---------|
| `Brochure_Generator` | Scrape a company site and write a short brochure |
| `Flight_Assistant` | Airline chat assistant with a ticket-price tool |
| `Audio_Encryptor` | Audio / encryption lab |
| `PY-CPP` | Python-to-C++ porting assistant |
| `RAG` | Insurellm RAG chatbot |
| `Simple_FinanceAnalyst` | Stock-research agent (Agno / Phidata) with Yahoo Finance tools |

## Setup

```powershell
uv sync
```

Put API keys in `.env` (this file is not committed):

```env
GROQ_API_KEY=your_groq_key
```

Run an app from this folder, for example:

```powershell
uv run python Simple_FinanceAnalyst/app.py
```
