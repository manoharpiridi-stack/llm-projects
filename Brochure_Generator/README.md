# Project 1: Company Brochure Generator

A Gradio app that scrapes a company website, picks the useful pages, and writes a short markdown brochure with an LLM.

## What it does

1. Fetches the landing page and its links.
2. Asks the selected model which links belong in a brochure (About, Products, Careers, and similar). It skips Terms of Service, Privacy, and email links.
3. Fetches those pages.
4. Asks the same model to write a markdown brochure for customers, investors, and recruits.

## Files

| File | Role |
|------|------|
| `Scrapers.py` | Downloads page text and collects links (`fetch_website_contents`, `get_links`). |
| `Generators.py` | LLM steps: `select_relevant_links` then `create_brochure`. |
| `app.py` | Gradio UI, model dropdown, API clients, and the two system prompts. |

`app.py` builds the client and prompts, then passes them into `create_brochure`:

- `company_name`, `url` — from the Gradio form
- `Chatai` — OpenAI-compatible client for the provider of the selected model
- `model` — API model id from the `MODELS` dict in `app.py`
- `brochure_system_prompt` — how to write the brochure (`BROCHURE_SYSTEM_PROMPT`)
- `System_Prompt` — how to choose relevant links (`LINK_SYSTEM_PROMPT`)

## UI

The form has:

- Company name
- Website URL
- **Model** dropdown
- **Generate brochure**

Models currently listed in `MODELS`:

| Dropdown label | Provider | Model id |
|----------------|----------|----------|
| Groq · GPT-OSS 120B (default) | Groq | `openai/gpt-oss-120b` |
| Groq · GPT-OSS 20B | Groq | `openai/gpt-oss-20b` |
| OpenRouter · GPT-4o mini | OpenRouter | `openai/gpt-4o-mini` |

Add or change entries in the `MODELS` dict in `app.py` to extend the dropdown.

While a run is in progress:

- The button changes to **Generating…** and stays disabled.
- The brochure area shows **Processing with [selected model]…**
- Gradio shows a progress indicator.

When it finishes, the button returns to **Generate brochure** and the markdown brochure replaces the processing message.

## Setup

From the parent folder (`LLM Projects`):

```powershell
uv sync
```

Put API keys in `LLM Projects/.env` (one level above this folder). The app loads that path automatically.

```env
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key
```

- Groq models need `GROQ_API_KEY`.
- The OpenRouter model needs `OPENROUTER_API_KEY`.

Do not commit `.env`.

## Run

From `LLM Projects`:

```powershell
uv run python "Project_1/app.py"
```

The app opens in the browser (or use the URL Gradio prints, usually `http://127.0.0.1:7860`).

Enter a company name and website (for example Hugging Face and `https://huggingface.co`), pick a model, then click **Generate brochure**. You can also press Enter in the URL box.

Generation can take a minute because it scrapes several pages and makes two model calls.

## Notes

- Page text is truncated (about 2,000 characters per page; the brochure prompt is truncated to 5,000 characters).
- Some sites block scrapers; if a page fails, that section is skipped and the brochure still runs on what was fetched.
- Groq JSON mode is used when selecting links (`response_format: json_object`).
