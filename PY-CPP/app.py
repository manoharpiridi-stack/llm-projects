import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

MODELS = {
    "Groq · GPT-OSS 120B": ("groq", "openai/gpt-oss-120b"),
    "Groq · GPT-OSS 20B": ("groq", "openai/gpt-oss-20b"),
    "Groq · Llama 3.3 70B": ("groq", "llama-3.3-70b-versatile"),
    "Gemini · 3.6 Flash": ("gemini", "gemini-3.6-flash"),
    "OpenRouter · GPT-OSS 120B (free)": ("openrouter", "openai/gpt-oss-120b:free"),
}
DEFAULT_MODEL = "Groq · GPT-OSS 120B"

SYSTEM_PROMPT = """
Your task is to convert Python code into high performance C++ code.
Respond only with C++ code. Do not provide any explanation other than occasional comments.
The C++ response needs to produce an identical output in the fastest possible time.
Print the result and the execution time in seconds, matching the Python program.
Do not use #include <bits/stdc++.h>. Use standard headers.
"""

PYTHON_SAMPLE = """# Be careful to support large numbers

def lcg(seed, a=1664525, c=1013904223, m=2**32):
    value = seed
    while True:
        value = (a * value + c) % m
        yield value

def max_subarray_sum(n, seed, min_val, max_val):
    lcg_gen = lcg(seed)
    random_numbers = [next(lcg_gen) % (max_val - min_val + 1) + min_val for _ in range(n)]
    max_sum = float('-inf')
    for i in range(n):
        current_sum = 0
        for j in range(i, n):
            current_sum += random_numbers[j]
            if current_sum > max_sum:
                max_sum = current_sum
    return max_sum

def total_max_subarray_sum(n, initial_seed, min_val, max_val):
    total_sum = 0
    lcg_gen = lcg(initial_seed)
    for _ in range(20):
        seed = next(lcg_gen)
        total_sum += max_subarray_sum(n, seed, min_val, max_val)
    return total_sum

n = 10000
initial_seed = 42
min_val = -10
max_val = 10

import time
start_time = time.time()
result = total_max_subarray_sum(n, initial_seed, min_val, max_val)
end_time = time.time()

print("Total Maximum Subarray Sum (20 runs):", result)
print("Execution Time: {:.6f} seconds".format(end_time - start_time))
"""


def get_client(provider):
    if provider == "groq":
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is missing from the .env file.")
        return OpenAI(api_key=key.strip(), base_url="https://api.groq.com/openai/v1")

    if provider == "gemini":
        key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY is missing from the .env file.")
        return OpenAI(
            api_key=key.strip(),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

    if provider == "openrouter":
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is missing from the .env file.")
        return OpenAI(api_key=key.strip(), base_url="https://openrouter.ai/api/v1")

    raise RuntimeError(f"Unknown provider: {provider}")


def user_prompt_for(python):
    return f"""
Port this Python code to C++ with the fastest possible implementation that produces identical output.
Respond only with C++ code. A single main() should print the same lines as Python.

Python code to port:

```python
{python}
```
"""


def strip_fences(text):
    reply = text.replace("```cpp", "").replace("```c++", "").replace("```", "")
    return reply.strip()


def port(model_choice, python):
    provider, model = MODELS[model_choice]
    client = get_client(provider)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt_for(python)},
        ],
    )
    return strip_fences(response.choices[0].message.content or "")


def run_python(code):
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer
    try:
        exec(code, {"__builtins__": __builtins__})
        return buffer.getvalue()
    except Exception as exc:
        return f"Error: {exc}"
    finally:
        sys.stdout = old_stdout


def refresh_windows_path():
    if os.name != "nt":
        return
    try:
        import winreg

        def read_path(root, subkey):
            with winreg.OpenKey(root, subkey) as key:
                value, _ = winreg.QueryValueEx(key, "Path")
                return value or ""

        machine = read_path(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        )
        user = read_path(winreg.HKEY_CURRENT_USER, "Environment")
        os.environ["PATH"] = ";".join(
            part for part in (machine, user, os.environ.get("PATH", "")) if part
        )
    except OSError:
        pass


def cpp_commands():
    refresh_windows_path()
    compiler = shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        raise RuntimeError(
            "No C++ compiler found. Install MinGW g++ or clang++ and add it to PATH."
        )
    exe = str(ROOT / ("main.exe" if os.name == "nt" else "main"))
    compile_cmd = [compiler, "-O3", "-std=c++17", str(ROOT / "main.cpp"), "-o", exe]
    return compile_cmd, [exe]


def compile_and_run(code):
    if not code or not code.strip():
        return "No C++ code yet. Port Python first."
    (ROOT / "main.cpp").write_text(code, encoding="utf-8")
    try:
        compile_cmd, run_cmd = cpp_commands()
        compiled = subprocess.run(
            compile_cmd, cwd=ROOT, check=True, text=True, capture_output=True
        )
        ran = subprocess.run(
            run_cmd, cwd=ROOT, check=True, text=True, capture_output=True
        )
        extra = compiled.stderr.strip()
        return (extra + "\n" if extra else "") + ran.stdout
    except subprocess.CalledProcessError as exc:
        return f"An error occurred:\n{exc.stderr or exc.stdout or exc}"
    except Exception as exc:
        return str(exc)


with gr.Blocks(title="Python to C++") as demo:
    gr.Markdown(
        "# Python to C++\n"
        "Port Python to C++ with a free-tier model, then run both to compare execution time. "
        "Needs a local C++ compiler (`g++` or `clang++`)."
    )
    with gr.Row():
        python = gr.Code(
            label="Python (original)",
            value=PYTHON_SAMPLE,
            language="python",
            lines=22,
        )
        cpp = gr.Code(label="C++ (generated)", value="", language="cpp", lines=22)

    with gr.Row():
        python_run = gr.Button("Run Python")
        model = gr.Dropdown(
            label="Model",
            choices=list(MODELS.keys()),
            value=DEFAULT_MODEL,
        )
        convert = gr.Button("Port to C++", variant="primary")
        cpp_run = gr.Button("Run C++")

    with gr.Row():
        python_out = gr.Textbox(label="Python result", lines=8)
        cpp_out = gr.Textbox(label="C++ result", lines=8)

    convert.click(fn=port, inputs=[model, python], outputs=[cpp])
    python_run.click(fn=run_python, inputs=[python], outputs=[python_out])
    cpp_run.click(fn=compile_and_run, inputs=[cpp], outputs=[cpp_out])

if __name__ == "__main__":
    demo.launch(inbrowser=True)
