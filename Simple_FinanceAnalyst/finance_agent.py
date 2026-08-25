"""Run the same agent in the terminal instead of the Gradio app."""

from agent import finance_agent

question = "Summarize NVDA stock price, key fundamentals, and recent performance."
finance_agent.print_response(question, stream=True)
