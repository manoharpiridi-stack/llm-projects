# Project 4: Python to C++

Week 4 Day 5 lab as a small Gradio app. A free-tier model ports Python to C++, then you run both locally and compare printed execution times.

## Run

From `LLM Projects`:

```powershell
uv run python Project_4/app.py
```

Uses keys from the parent `.env`: `GROQ_API_KEY` (default), or `GOOGLE_API_KEY` / `OPENROUTER_API_KEY` for those dropdown options.

Install MinGW `g++` or `clang++` and keep it on PATH to use **Run C++**.
