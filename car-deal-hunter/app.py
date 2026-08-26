import json
import sys
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(ROOT))

from car_hunter.config import DEAL_THRESHOLD, METRICS_PATH
from car_hunter.framework import DealHunter
from car_hunter.listings import listing_from_row


hunter = None


def get_hunter() -> DealHunter:
    global hunter
    if hunter is None:
        hunter = DealHunter()
    return hunter


def estimate(year, manufacturer, odometer, condition, fuel, drive, body_type, state, extra):
    row = {
        "year": int(year),
        "manufacturer": manufacturer,
        "odometer": float(odometer),
        "price": 0,
        "condition": condition,
        "fuel": fuel,
        "transmission": "automatic",
        "drive": drive,
        "type": body_type,
        "cylinders": "unknown",
        "paint_color": "unknown",
        "title_status": "clean",
        "state": state,
        "car_age": 2026 - int(year),
    }
    listing = listing_from_row(row)
    if extra and extra.strip():
        listing.description = listing.description + " " + extra.strip()
        listing.make_prompt()
    estimate_value, parts = get_hunter().estimate_listing(listing)
    text = listing.description
    breakdown = "\n".join(f"{name}: ${value:,.0f}" for name, value in parts.items())
    return f"${estimate_value:,.0f}", breakdown, text


def hunt(n, threshold):
    app = get_hunter()
    app.planner.threshold = float(threshold)
    found = app.hunt(n=int(n))
    if not found:
        return "No listings beat the discount threshold. Try a lower threshold or a larger scan."
    lines = []
    for item in found:
        lines.append(
            f"**{item.deal.listing.title}** — ask ${item.deal.asking_price:,.0f}, "
            f"fair ${item.estimate:,.0f}, discount **${item.discount:,.0f}**\n"
            f"{item.deal.listing.description}\n"
        )
    return "\n\n".join(lines)


def metrics_md():
    if not METRICS_PATH.exists():
        return "Run `python scripts/train_baselines.py` first."
    rows = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    header = "| model | n | MAE | RMSE | R² |\n|---|---:|---:|---:|---:|"
    body = "\n".join(
        f"| {r['title']} | {r['n']} | ${r['mae']:,.0f} | ${r['rmse']:,.0f} | {r['r2']:.3f} |"
        for r in rows
    )
    return header + "\n" + body


with gr.Blocks(title="Used Car Deal Hunter") as demo:
    gr.Markdown(
        "# Used Car Deal Hunter\n"
        "Week 6–8 capstone: Craigslist listings → Random Forest + RAG (+ optional local LLM). "
        "No OpenAI. No Modal."
    )
    with gr.Tab("Estimate"):
        with gr.Row():
            year = gr.Number(value=2018, label="Year", precision=0)
            manufacturer = gr.Textbox(value="honda", label="Make")
            odometer = gr.Number(value=65000, label="Miles")
        with gr.Row():
            condition = gr.Dropdown(
                ["excellent", "good", "fair", "like new", "salvage"],
                value="good",
                label="Condition",
            )
            fuel = gr.Dropdown(["gas", "diesel", "hybrid", "electric", "other"], value="gas", label="Fuel")
            drive = gr.Dropdown(["fwd", "rwd", "4wd"], value="fwd", label="Drive")
        with gr.Row():
            body_type = gr.Dropdown(
                ["sedan", "suv", "truck", "hatchback", "coupe", "wagon", "van", "convertible"],
                value="sedan",
                label="Body",
            )
            state = gr.Textbox(value="ca", label="State")
        extra = gr.Textbox(label="Optional extra listing text", lines=3)
        btn = gr.Button("Estimate fair price")
        price_out = gr.Textbox(label="Ensemble estimate")
        parts_out = gr.Textbox(label="Agent breakdown")
        text_out = gr.Textbox(label="Listing text sent to the models")
        btn.click(
            estimate,
            [year, manufacturer, odometer, condition, fuel, drive, body_type, state, extra],
            [price_out, parts_out, text_out],
        )
    with gr.Tab("Hunt deals"):
        n = gr.Slider(4, 20, value=8, step=1, label="Listings to scan")
        threshold = gr.Number(value=DEAL_THRESHOLD, label="Min discount ($)")
        hunt_btn = gr.Button("Scan test-set market feed")
        hunt_out = gr.Markdown()
        hunt_btn.click(hunt, [n, threshold], [hunt_out])
    with gr.Tab("Metrics"):
        gr.Markdown(metrics_md())

if __name__ == "__main__":
    demo.launch(share=True, server_name="127.0.0.1", server_port=7861)
