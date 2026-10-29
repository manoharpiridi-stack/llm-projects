import sys
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Pro_Implementation.answer import (
    DEFAULT_MODEL,
    MODELS,
    answer_question,
    get_client,
)

# Switch the import above to Pro_Implementation.answer to run the pro pipeline.
USING_PRO = answer_question.__module__.startswith("Pro_Implementation")

if USING_PRO:
    PAGE_INTRO = (
        "# Insurellm Expert Assistant (pro)\n"
        "Greetings stay as chat. Real questions use query rewrite, dual retrieve, and rerank. "
        "Build the index with `uv run python RAG/Pro_Implementation/ingest.py`."
    )
    EMPTY_CONTEXT = (
        "No knowledge-base lookup for this message. "
        "Retrieval runs only when the question needs Insurellm facts."
    )
else:
    PAGE_INTRO = (
        "# Insurellm Expert Assistant (normal)\n"
        "Every message is embedded and the closest chunks are retrieved, then the model answers. "
        "No query rewrite or rerank. Optional: "
        "`uv run python RAG/Implementation/ingest.py` to rebuild `vector_db`."
    )
    EMPTY_CONTEXT = "No retrieved passages."

load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")


def format_context(context):
    if not context:
        return EMPTY_CONTEXT
    parts = []
    for doc in context:
        source = doc.metadata.get("source", "unknown")
        parts.append(f"**Source:** `{source}`\n\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def put_message_in_chatbot(message, history):
    message = (message or "").strip()
    if not message:
        return "", history
    return "", history + [{"role": "user", "content": message}]


def chat(history, model_choice):
    if not history:
        return history, "Ask a question about Insurellm."
    last_message = history[-1]["content"]
    prior = history[:-1]
    try:
        provider, model = MODELS[model_choice]
        client = get_client(provider)
        answer, context = answer_question(
            last_message, prior, client=client, model=model
        )
    except Exception as exc:
        history.append({"role": "assistant", "content": f"Could not answer that:\n\n{exc}"})
        return history, str(exc)
    history.append({"role": "assistant", "content": answer or "The model returned an empty answer."})
    return history, format_context(context)


def mark_busy():
    return gr.update(interactive=False, value="Thinking…")


def mark_ready():
    return gr.update(interactive=True, value="Ask")


with gr.Blocks(title="Insurellm RAG Assistant") as demo:
    gr.Markdown(PAGE_INTRO)
    with gr.Row():
        with gr.Column(scale=1):
            chatbot = gr.Chatbot(
                label="Conversation",
                height=520,
                type="messages",
                show_copy_button=True,
            )
            message = gr.Textbox(
                label="Your question",
                placeholder="What is Carllm?",
            )
            model_choice = gr.Dropdown(
                label="Model",
                choices=list(MODELS.keys()),
                value=DEFAULT_MODEL,
            )
            ask_button = gr.Button("Ask", variant="primary")
        with gr.Column(scale=1):
            context_markdown = gr.Markdown(
                label="Retrieved context",
                value="Retrieved passages will appear here.",
            )

    ask_event = ask_button.click(
        fn=mark_busy,
        outputs=ask_button,
    ).then(
        fn=put_message_in_chatbot,
        inputs=[message, chatbot],
        outputs=[message, chatbot],
    ).then(
        fn=chat,
        inputs=[chatbot, model_choice],
        outputs=[chatbot, context_markdown],
        show_progress="full",
    ).then(
        fn=mark_ready,
        outputs=ask_button,
    )
    message.submit(
        fn=mark_busy,
        outputs=ask_button,
    ).then(
        fn=put_message_in_chatbot,
        inputs=[message, chatbot],
        outputs=[message, chatbot],
    ).then(
        fn=chat,
        inputs=[chatbot, model_choice],
        outputs=[chatbot, context_markdown],
        show_progress="full",
    ).then(
        fn=mark_ready,
        outputs=ask_button,
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)
