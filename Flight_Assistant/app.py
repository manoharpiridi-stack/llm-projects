import json
import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

MODEL = os.getenv("FLIGHT_MODEL", "openai/gpt-oss-120b")

SYSTEM_MESSAGE = """
You are a helpful assistant for an airline called FlightAI.
Give short, courteous answers, no more than 1 sentence.
Always be accurate. If you don't know the answer, say so.
You can look up return ticket prices with the get_ticket_price tool.
"""

TICKET_PRICES = {
    "london": "$799",
    "paris": "$899",
    "tokyo": "$1400",
    "berlin": "$499",
}

PRICE_TOOL = {
    "name": "get_ticket_price",
    "description": "Get the price of a return ticket to the destination city.",
    "parameters": {
        "type": "object",
        "properties": {
            "destination_city": {
                "type": "string",
                "description": "The city that the customer wants to travel to",
            },
        },
        "required": ["destination_city"],
        "additionalProperties": False,
    },
}
TOOLS = [{"type": "function", "function": PRICE_TOOL}]


def get_client():
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        return OpenAI(
            api_key=groq_key.strip(),
            base_url="https://api.groq.com/openai/v1",
        ), os.getenv("FLIGHT_MODEL", "qwen/qwen3.6-27b")

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        return OpenAI(
            api_key=openrouter_key.strip(),
            base_url="https://openrouter.ai/api/v1",
        ), os.getenv("FLIGHT_MODEL", "openai/gpt-4o-mini")

    raise RuntimeError(
        "No API key found. Add GROQ_API_KEY or OPENROUTER_API_KEY to .env "
        "(or Hugging Face Space secrets)."
    )


def get_ticket_price(destination_city):
    price = TICKET_PRICES.get(destination_city.lower(), "Unknown ticket price")
    return f"The price of a ticket to {destination_city} is {price}"


def handle_tool_calls(message):
    responses = []
    for tool_call in message.tool_calls:
        if tool_call.function.name == "get_ticket_price":
            arguments = json.loads(tool_call.function.arguments)
            city = arguments.get("destination_city")
            responses.append(
                {
                    "role": "tool",
                    "content": get_ticket_price(city),
                    "tool_call_id": tool_call.id,
                }
            )
    return responses


def chat(message, history):
    history = [{"role": h["role"], "content": h["content"]} for h in history]
    messages = (
        [{"role": "system", "content": SYSTEM_MESSAGE}]
        + history
        + [{"role": "user", "content": message}]
    )
    try:
        client, model = get_client()
        response = client.chat.completions.create(
            model=model, messages=messages, tools=TOOLS
        )
        while response.choices[0].finish_reason == "tool_calls":
            assistant_message = response.choices[0].message
            messages.append(assistant_message)
            messages.extend(handle_tool_calls(assistant_message))
            response = client.chat.completions.create(
                model=model, messages=messages, tools=TOOLS
            )
        return response.choices[0].message.content
    except Exception as exc:
        return f"Sorry, I could not answer that: {exc}"


demo = gr.ChatInterface(
    fn=chat,
    type="messages",
    title="FlightAI Assistant",
    description=(
        "Ask about flights. Sample return fares: London $799, Paris $899, "
        "Tokyo $1400, Berlin $499."
    ),
    examples=[
        "How much is a ticket to Paris?",
        "What's the fare to Tokyo?",
        "Do you fly to Berlin?",
    ],
)

if __name__ == "__main__":
    demo.launch(inbrowser=True)
