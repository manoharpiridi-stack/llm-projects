import os
import sys
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Generators import create_brochure

load_dotenv(ROOT.parent / ".env")

LINK_SYSTEM_PROMPT = """
You are provided with a list of links found on a webpage.
Decide which links are most relevant for a company brochure,
such as About, Company, Products, Customers, Careers/Jobs, or Contact pages.
Do not include Terms of Service, Privacy Policy, or email links.
Respond in JSON using this shape:
{
    "links": [
        {"type": "about page", "url": "https://full.url/goes/here/about"},
        {"type": "careers page", "url": "https://another.full.url/careers"}
    ]
}
"""

BROCHURE_SYSTEM_PROMPT = """
You are an assistant that analyzes the contents of several relevant pages from a company website
and creates a short brochure about the company for prospective customers, investors, and recruits.
Respond in markdown without wrapping the whole brochure in a code fence.
Include details of company culture, customers, and careers/jobs when that information is available.
"""

MODELS = {
    "Groq · GPT-OSS 120B": ("groq", "openai/gpt-oss-120b"),
    "Groq · GPT-OSS 20B": ("groq", "openai/gpt-oss-20b"),
    "OpenRouter · GPT-4o mini": ("openrouter", "openai/gpt-4o-mini"),
}
DEFAULT_MODEL = "Groq · GPT-OSS 120B"


def get_client(provider):
    if provider == "groq":
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise RuntimeError("GROQ_API_KEY is missing from the .env file.")
        return OpenAI(
            api_key=groq_key.strip(),
            base_url="https://api.groq.com/openai/v1",
        )

    if provider == "openrouter":
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY is missing from the .env file.")
        return OpenAI(
            api_key=openrouter_key.strip(),
            base_url="https://openrouter.ai/api/v1",
        )

    raise RuntimeError(f"Unknown provider: {provider}")


def generate_brochure(company_name, url, model_choice):
    company_name = (company_name or "").strip()
    url = (url or "").strip()
    if not company_name or not url:
        yield "Please enter both a company name and a website URL."
        return
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    provider, model = MODELS[model_choice]
    yield (
        f"⏳ **Processing with {model_choice}…** Scraping the website, "
        "selecting relevant pages, and writing the brochure. This can take a minute."
    )
    try:
        client = get_client(provider)
        brochure = create_brochure(
            company_name,
            url,
            client,
            model,
            BROCHURE_SYSTEM_PROMPT,
            LINK_SYSTEM_PROMPT,
        )
        yield brochure or "The model returned an empty brochure."
    except Exception as exc:
        yield f"Could not generate the brochure:\n\n{exc}"


def mark_button_busy():
    return gr.update(interactive=False, value="Generating…")


def mark_button_ready():
    return gr.update(interactive=True, value="Generate brochure")


with gr.Blocks(title="Company Brochure Generator") as demo:
    gr.Markdown(
        "# Company Brochure Generator\n"
        "Enter a company name and website. The app scrapes relevant pages and writes a short markdown brochure."
    )
    with gr.Row():
        company_name = gr.Textbox(
            label="Company name",
            placeholder="Hugging Face",
        )
        website_url = gr.Textbox(
            label="Website URL",
            placeholder="https://huggingface.co",
        )
        model_choice = gr.Dropdown(
            label="Model",
            choices=list(MODELS.keys()),
            value=DEFAULT_MODEL,
            interactive=True,
        )
    generate_button = gr.Button("Generate brochure", variant="primary")
    brochure_output = gr.Markdown(label="Brochure")
    # Gradio Event Handlers
    # When the user clicks the Generate button
    generate_button.click(
        fn=mark_button_busy,
        outputs=generate_button,
    ).then(
        fn=generate_brochure,
        inputs=[company_name, website_url, model_choice],
        outputs=brochure_output,
        show_progress="full",
    ).then(
        fn=mark_button_ready,
        outputs=generate_button,
    )
    # When the user presses Enter in the website URL input
    website_url.submit(
        fn=mark_button_busy,
        outputs=generate_button,
    ).then(
        fn=generate_brochure,
        inputs=[company_name, website_url, model_choice],
        outputs=brochure_output,
        show_progress="full",
    ).then(
        fn=mark_button_ready,
        outputs=generate_button,
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)
