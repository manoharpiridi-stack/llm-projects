import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

TRANSCRIBE_MODEL = os.getenv("TRANSCRIBE_MODEL", "whisper-large-v3-turbo")

MODELS = {
    "Groq · GPT-OSS 120B": ("groq", "openai/gpt-oss-120b"),
    "Groq · GPT-OSS 20B": ("groq", "openai/gpt-oss-20b"),
    "OpenRouter · GPT-4o mini": ("openrouter", "openai/gpt-4o-mini"),
}
DEFAULT_MODEL = "Groq · GPT-OSS 120B"

SYSTEM_MESSAGE = """
You produce minutes of meetings from timestamped transcripts, in markdown without code blocks.
Always include:
- total meeting duration (use the provided duration; do not invent a different length)
- a summary with attendees, location and date when they appear in the transcript
- discussion points, each starting with a timestamp in [MM:SS] or [HH:MM:SS] matching the transcript
- takeaways
- action items with owners
Use only timestamps that appear in the transcript. Group nearby lines into coherent discussion points.
"""

DEFAULT_CONTEXT = (
    "This is an extract transcript of a Denver council meeting. "
    "Include attendees, location, and date in the summary when they are mentioned."
)


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


def groq_client():
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise RuntimeError(
            "GROQ_API_KEY is required for audio transcription. "
            "Add it to the .env file in LLM Projects."
        )
    return OpenAI(
        api_key=groq_key.strip(),
        base_url="https://api.groq.com/openai/v1",
    )


def format_timestamp(seconds):
    total = int(round(max(0.0, float(seconds or 0))))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_duration(seconds):
    total = int(round(max(0.0, float(seconds or 0))))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes or hours:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    clock = format_timestamp(total)
    return f"{clock} ({', '.join(parts)})"


def segment_value(segment, key, default=None):
    if isinstance(segment, dict):
        return segment.get(key, default)
    return getattr(segment, key, default)


def transcribe_audio(audio_path):
    client = groq_client()
    with open(audio_path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            model=TRANSCRIBE_MODEL,
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = list(getattr(result, "segments", None) or [])
    duration_seconds = getattr(result, "duration", None)
    if duration_seconds is None and segments:
        duration_seconds = segment_value(segments[-1], "end", 0) or 0

    lines = []
    for segment in segments:
        start = format_timestamp(segment_value(segment, "start", 0))
        text = (segment_value(segment, "text", "") or "").strip()
        if text:
            lines.append(f"[{start}] {text}")

    transcription = "\n".join(lines).strip() or (result.text or "").strip()
    duration_label = format_duration(duration_seconds)
    display_text = f"Meeting duration: {duration_label}\n\n{transcription}".strip()
    return display_text, transcription, duration_label


def write_minutes(transcription, duration_label, meeting_context, model_choice):
    provider, model = MODELS[model_choice]
    client = get_client(provider)
    context = (meeting_context or "").strip() or DEFAULT_CONTEXT
    user_prompt = f"""
{context}

Total meeting duration: {duration_label}

Please write minutes in markdown without code blocks. Required sections:

## Meeting duration
State the total duration exactly as: {duration_label}

## Summary
Include attendees, location, and date when they are mentioned.

## Discussion points
Each bullet must start with the timestamp from the transcript, like `- [03:42] Topic...`
Use the timestamp of the first transcript line that belongs to that point.

## Takeaways

## Action items
Include owners when named.

Timestamped transcription:
{transcription}
"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def process_audio(audio_path, meeting_context, model_choice):
    if not audio_path:
        yield "", "Please upload an audio file first."
        return

    yield "Transcribing audio…", "Waiting for the transcript…"
    try:
        display_text, transcription, duration_label = transcribe_audio(audio_path)
    except Exception as exc:
        yield "", f"Could not transcribe the audio:\n\n{exc}"
        return

    if not transcription:
        yield "", "The transcription was empty. Try a clearer recording."
        return

    yield display_text, f"Writing meeting minutes… Total duration: {duration_label}"
    try:
        minutes = write_minutes(
            transcription, duration_label, meeting_context, model_choice
        )
        yield display_text, minutes or "The model returned empty minutes."
    except Exception as exc:
        yield display_text, f"Transcription succeeded, but minutes failed:\n\n{exc}"


def mark_button_busy():
    return gr.update(interactive=False, value="Processing…")


def mark_button_ready():
    return gr.update(interactive=True, value="Transcribe and summarize")


with gr.Blocks(title="Meeting Minutes from Audio") as demo:
    gr.Markdown(
        "# Meeting Minutes from Audio\n"
        "Upload a recording. The app transcribes it with Whisper (with timestamps), "
        "then writes markdown minutes that include total duration and timestamped discussion points."
    )
    with gr.Row():
        audio_input = gr.Audio(
            label="Meeting audio",
            type="filepath",
            sources=["upload", "microphone"],
        )
        with gr.Column():
            meeting_context = gr.Textbox(
                label="Meeting context (optional)",
                value=DEFAULT_CONTEXT,
                lines=4,
            )
            model_choice = gr.Dropdown(
                label="Minutes model",
                choices=list(MODELS.keys()),
                value=DEFAULT_MODEL,
            )
            run_button = gr.Button("Transcribe and summarize", variant="primary")

    transcription_output = gr.Textbox(
        label="Timestamped transcription",
        lines=12,
        show_copy_button=True,
    )
    minutes_output = gr.Markdown(label="Minutes")

    run_button.click(
        fn=mark_button_busy,
        outputs=run_button,
    ).then(
        fn=process_audio,
        inputs=[audio_input, meeting_context, model_choice],
        outputs=[transcription_output, minutes_output],
        show_progress="full",
    ).then(
        fn=mark_button_ready,
        outputs=run_button,
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)
