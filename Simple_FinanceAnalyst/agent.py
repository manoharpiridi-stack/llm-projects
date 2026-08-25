"""
A tiny financial agent.

Phidata was renamed to Agno. The idea is the same:

  1. Pick an LLM (here: Groq).
  2. Give it tools that can fetch live stock data (Yahoo Finance).
  3. Ask a question. The model calls a tool when it needs a number,
     then writes the answer from that data.

You do not write the tool-calling loop yourself. Agno does that.
"""

from pathlib import Path

from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.yfinance import YFinanceTools

# Load GROQ_API_KEY from this folder or the parent LLM Projects folder.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

# Yahoo Finance helpers: price, company info, fundamentals, news, and more.
finance_tools = YFinanceTools(all=True)

# The agent = model + tools + a short job description.
finance_agent = Agent(
    name="Finance Agent",
    model=Groq(id="openai/gpt-oss-120b"),
    tools=[finance_tools],
    description="You look up live stock data and explain it in plain language.",
    instructions=[
        "Use the Yahoo Finance tools for prices, fundamentals, and performance.",
        "Do not invent numbers.",
        "Show figures in markdown tables when that helps.",
        "Do not give personalized buy or sell advice.",
    ],
    markdown=True,
)


def ask(question: str) -> str:
    """Send one question to the agent and return its text answer."""
    result = finance_agent.run(question)
    return result.content or "The model returned an empty answer."
