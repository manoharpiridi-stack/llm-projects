# Used Car Deal Hunter

A Weeks 6–8 capstone from the LLM Engineering course, rebuilt for **used cars** and a **$0 API budget**.

It estimates a fair price from a listing, then hunts the held-out test set for cars listed well below that estimate.

**Not used:** OpenAI fine-tuning, GPT APIs, Modal GPU hosting.

**Used instead:** public Craigslist data, scikit-learn, local Chroma RAG, optional Ollama, optional Google Colab QLoRA.

## Architecture

```text
Craigslist listings (Hugging Face)
        │
        ▼
  listing text from structured fields     ← Week 6 curation
        │
        ├─► Random Forest (year, miles, make, …)     ← Week 6 baseline
        ├─► Chroma RAG + kNN / local LLM             ← Week 8 FrontierAgent, no OpenAI
        └─► optional QLoRA adapter (Colab T4)        ← Week 7, no Modal
                │
                ▼
           EnsembleAgent
                │
     Scanner (test-set feed) → Planner → alerts + Gradio
```

The cleaned public dataset dropped the original free-text ad and model name. Listings are rebuilt from year, make, miles, condition, fuel, drivetrain, body, and state — the same idea as the course “LLM rewrite” step, without paying for a rewrite model.

## Setup (from the course repo)

From this folder:

```powershell
cd "H:\New folder\Projects\LLM Projects\car-deal-hunter"
copy .env.example .env
uv sync
uv run python scripts\prepare_data.py
uv run python scripts\train_baselines.py
uv run python scripts\build_index.py
uv run python app.py
```

Data and the Random Forest are already prepared if you copied `data/` with the project. In that case you can skip the three scripts and run `uv run python app.py`.

`prepare_data.py` downloads `Yoad22/craigslist-used-cars-eda` (CC-BY-4.0, from Austin Reese’s Kaggle Craigslist scrape) and writes an 8k/1k/1k lite split. Use `--full` if your machine can handle more.

## What each piece maps to in the course

| Course | This project |
|---|---|
| Week 6 data curation | `car_hunter/curator.py` |
| Week 6 RF / eval | `scripts/train_baselines.py`, Metrics tab |
| Week 7 QLoRA | `notebooks/qlora_colab.ipynb` on **free Colab T4** |
| Week 8 Specialist on Modal | local adapter folder or Ollama |
| Week 8 RAG + ensemble | `car_hunter/agents/rag.py`, `ensemble.py` |
| Week 8 scanner / planner / Gradio | test-set feed + `app.py` |

The scanner does **not** scrape live marketplaces. It walks the test split so the demo is legal, reproducible, and free.

## Optional: QLoRA on Colab (still free)

1. `python scripts/export_sft.py`
2. Upload `data/train_sft.jsonl` to Colab (or Drive)
3. Open `notebooks/qlora_colab.ipynb`, set runtime to T4
4. Download the adapter into `data/qlora_adapter/`
5. Restart the app — `SpecialistAgent` will load it if `adapter_config.json` is present

The notebook fine-tunes **Qwen2.5-1.5B-Instruct** (ungated on Hugging Face). Llama 3.2 needs a HF license click-through; skip it if you do not want that.

## Optional free LLM APIs

In `.env`:

```
LLM_PROVIDER=groq
GROQ_API_KEY=...
```

or

```
LLM_PROVIDER=gemini
GOOGLE_API_KEY=...
```

Groq and Gemini have free tiers. They are optional. The forest + kNN path runs with no keys.

## GitHub README extras to add later

- Paste the MAE table from the Metrics tab
- A 20-second GIF of the Gradio Hunt tab
- Link the Hugging Face dataset and, if you train QLoRA, your adapter repo

When you split this folder into its own repository, copy `car-deal-hunter/` only — do not publish the whole course tree or any `.env` file.
