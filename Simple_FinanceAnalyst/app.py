"""Gradio chat window that talks to the finance agent."""

from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from agent import ask

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")


def chat(message, history):
    # Gradio already stores history in the UI.
    # Each new question is sent to the agent as-is.
    try:
        return ask(message)
    except Exception as exc:
        return f"Sorry, I could not look that up: {exc}"


demo = gr.ChatInterface(
    fn=chat,
    type="messages",
    title="Financial Analysis Agent",
    description=(
        "Ask about stock prices, company fundamentals, or recent performance. "
        "The agent (Agno, formerly Phidata) fetches live data from Yahoo Finance."
    ),
    examples=[
        "What is NVDA's current price?",
        "Summarize Apple fundamentals: P/E, margins, and revenue.",
        "How has MSFT performed recently?",
        "Compare GOOGL and AMZN on valuation.",
    ],
)

if __name__ == "__main__":
    demo.launch(inbrowser=True)
