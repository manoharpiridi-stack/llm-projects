import sys
from collections import defaultdict
from pathlib import Path

import gradio as gr
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Evaluation.eval import (
    ACTIVE_PIPELINE,
    DEFAULT_MODEL,
    MODELS,
    PIPELINE_MODULE,
    evaluate_all_answers,
    evaluate_all_retrieval,
)

load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

MRR_GREEN = 0.9
MRR_AMBER = 0.75
NDCG_GREEN = 0.9
NDCG_AMBER = 0.75
COVERAGE_GREEN = 90.0
COVERAGE_AMBER = 75.0
ANSWER_GREEN = 4.5
ANSWER_AMBER = 4.0

CATEGORY_ORDER = [
    "direct_fact",
    "temporal",
    "comparative",
    "numerical",
    "relationship",
    "spanning",
    "holistic",
]


def get_color(value: float, metric_type: str) -> str:
    if metric_type == "mrr":
        green, amber = MRR_GREEN, MRR_AMBER
    elif metric_type == "ndcg":
        green, amber = NDCG_GREEN, NDCG_AMBER
    elif metric_type == "coverage":
        green, amber = COVERAGE_GREEN, COVERAGE_AMBER
    else:
        green, amber = ANSWER_GREEN, ANSWER_AMBER
    if value >= green:
        return "green"
    if value >= amber:
        return "orange"
    return "red"


def format_metric_html(
    label: str,
    value: float,
    metric_type: str,
    is_percentage: bool = False,
    score_format: bool = False,
) -> str:
    color = get_color(value, metric_type)
    if is_percentage:
        value_str = f"{value:.1f}%"
    elif score_format:
        value_str = f"{value:.2f}/5"
    else:
        value_str = f"{value:.4f}"
    return f"""
    <div style="margin: 10px 0; padding: 15px; background-color: #f5f5f5; border-radius: 8px; border-left: 5px solid {color};">
        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">{label}</div>
        <div style="font-size: 28px; font-weight: bold; color: {color};">{value_str}</div>
    </div>
    """


def empty_chart(y_column):
    return pd.DataFrame(columns=["Category", y_column])


def scores_by_category(mapping, y_column):
    rows = []
    seen = set()
    for category in CATEGORY_ORDER:
        if category not in mapping:
            continue
        scores = mapping[category]
        rows.append({"Category": category, y_column: sum(scores) / len(scores)})
        seen.add(category)
    for category, scores in mapping.items():
        if category in seen:
            continue
        rows.append({"Category": category, y_column: sum(scores) / len(scores)})
    return pd.DataFrame(rows)


def run_retrieval_evaluation(progress=gr.Progress()):
    total_mrr = 0.0
    total_ndcg = 0.0
    total_coverage = 0.0
    category_mrr = defaultdict(list)
    count = 0

    for test, result, prog_value in evaluate_all_retrieval():
        count += 1
        total_mrr += result.mrr
        total_ndcg += result.ndcg
        total_coverage += result.keyword_coverage
        category_mrr[test.category].append(result.mrr)
        progress(prog_value, desc=f"Evaluating retrieval {count}…")

    if count == 0:
        return "<p>No tests found in Evaluation/tests.jsonl.</p>", empty_chart("Average MRR")

    avg_mrr = total_mrr / count
    avg_ndcg = total_ndcg / count
    avg_coverage = total_coverage / count
    final_html = f"""
    <div style="padding: 0;">
        {format_metric_html("Mean Reciprocal Rank (MRR)", avg_mrr, "mrr")}
        {format_metric_html("Normalized DCG (nDCG)", avg_ndcg, "ndcg")}
        {format_metric_html("Keyword Coverage", avg_coverage, "coverage", is_percentage=True)}
        <div style="margin-top: 20px; padding: 10px; background-color: #d4edda; border-radius: 5px; text-align: center; border: 1px solid #c3e6cb;">
            <span style="font-size: 14px; color: #155724; font-weight: bold;">Evaluation complete: {count} tests</span>
        </div>
    </div>
    """
    return final_html, scores_by_category(category_mrr, "Average MRR")


def run_answer_evaluation(model_choice, progress=gr.Progress()):
    total_accuracy = 0.0
    total_completeness = 0.0
    total_relevance = 0.0
    category_accuracy = defaultdict(list)
    count = 0

    for test, result, prog_value in evaluate_all_answers(model_choice=model_choice):
        count += 1
        total_accuracy += result.accuracy
        total_completeness += result.completeness
        total_relevance += result.relevance
        category_accuracy[test.category].append(result.accuracy)
        progress(prog_value, desc=f"Evaluating answers {count}…")

    if count == 0:
        return "<p>No tests found in Evaluation/tests.jsonl.</p>", empty_chart("Average Accuracy")

    avg_accuracy = total_accuracy / count
    avg_completeness = total_completeness / count
    avg_relevance = total_relevance / count
    final_html = f"""
    <div style="padding: 0;">
        {format_metric_html("Accuracy", avg_accuracy, "accuracy", score_format=True)}
        {format_metric_html("Completeness", avg_completeness, "completeness", score_format=True)}
        {format_metric_html("Relevance", avg_relevance, "relevance", score_format=True)}
        <div style="margin-top: 20px; padding: 10px; background-color: #d4edda; border-radius: 5px; text-align: center; border: 1px solid #c3e6cb;">
            <span style="font-size: 14px; color: #155724; font-weight: bold;">Evaluation complete: {count} tests</span>
        </div>
    </div>
    """
    return final_html, scores_by_category(category_accuracy, "Average Accuracy")


with gr.Blocks(title="Insurellm RAG Evaluation") as demo:
    gr.Markdown(
        "# Insurellm RAG Evaluation\n"
        f"**Active pipeline: {ACTIVE_PIPELINE}** (`{PIPELINE_MODULE}`).\n\n"
        "`tests.jsonl` now has ~150 questions in seven categories: "
        "direct_fact, temporal, comparative, numerical, relationship, spanning, and holistic. "
        "**Spanning** (multi-hop) and **holistic** (counts/totals across many docs) are where "
        "top-k RAG usually drops. Retrieval is one search per question; answer eval calls the "
        "model and a judge for every test and can take a long time. "
        "Switch the import in `Evaluation/eval.py`, restart, and compare the same category bars."
    )

    gr.Markdown("## Retrieval")
    retrieval_button = gr.Button("Run retrieval evaluation", variant="primary")
    with gr.Row():
        retrieval_metrics = gr.HTML(
            "<div style='padding: 20px; text-align: center; color: #999;'>Click Run retrieval evaluation.</div>"
        )
        retrieval_chart = gr.BarPlot(
            x="Category",
            y="Average MRR",
            title="Average MRR by category",
            y_lim=[0, 1],
            height=480,
        )

    gr.Markdown("## Answers")
    answer_model = gr.Dropdown(
        label="Judge / answer model",
        choices=list(MODELS.keys()),
        value=DEFAULT_MODEL,
    )
    answer_button = gr.Button("Run answer evaluation", variant="primary")
    with gr.Row():
        answer_metrics = gr.HTML(
            "<div style='padding: 20px; text-align: center; color: #999;'>Click Run answer evaluation.</div>"
        )
        answer_chart = gr.BarPlot(
            x="Category",
            y="Average Accuracy",
            title="Average accuracy by category",
            y_lim=[1, 5],
            height=480,
        )

    retrieval_button.click(
        fn=run_retrieval_evaluation,
        outputs=[retrieval_metrics, retrieval_chart],
    )
    answer_button.click(
        fn=run_answer_evaluation,
        inputs=[answer_model],
        outputs=[answer_metrics, answer_chart],
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)
