import math
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Evaluation.test import TestQuestion, load_tests

# Switch this import, then restart evaluator.py, to compare pipelines:
#   Implementation.answer       -> normal (vector_db)
#   Pro_Implementation.answer   -> pro (preprocessed_db)
from Pro_Implementation.answer import (
    DEFAULT_MODEL,
    MODELS,
    answer_question,
    fetch_context,
    get_client,
)

load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

ACTIVE_PIPELINE = (
    "pro" if fetch_context.__module__.startswith("Pro_Implementation") else "normal"
)
PIPELINE_MODULE = fetch_context.__module__
print(f"RAG eval pipeline: {ACTIVE_PIPELINE} ({PIPELINE_MODULE})")


class RetrievalEval(BaseModel):
    mrr: float = Field(description="Mean Reciprocal Rank - average across all keywords")
    ndcg: float = Field(description="Normalized Discounted Cumulative Gain (binary relevance)")
    keywords_found: int = Field(description="Number of keywords found in top-k results")
    total_keywords: int = Field(description="Total number of keywords to find")
    keyword_coverage: float = Field(description="Percentage of keywords found")


class AnswerEval(BaseModel):
    feedback: str = Field(description="Concise feedback on the answer quality")
    accuracy: float = Field(description="Factual accuracy vs the reference answer, 1 to 5")
    completeness: float = Field(description="How completely the reference facts are covered, 1 to 5")
    relevance: float = Field(description="How directly the answer addresses the question, 1 to 5")


def calculate_mrr(keyword: str, retrieved_docs: list) -> float:
    keyword_lower = keyword.lower()
    for rank, doc in enumerate(retrieved_docs, start=1):
        if keyword_lower in doc.page_content.lower():
            return 1.0 / rank
    return 0.0


def calculate_dcg(relevances: list[int], k: int) -> float:
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        dcg += relevances[i] / math.log2(i + 2)
    return dcg


def calculate_ndcg(keyword: str, retrieved_docs: list, k: int = 10) -> float:
    keyword_lower = keyword.lower()
    relevances = [
        1 if keyword_lower in doc.page_content.lower() else 0 for doc in retrieved_docs[:k]
    ]
    dcg = calculate_dcg(relevances, k)
    idcg = calculate_dcg(sorted(relevances, reverse=True), k)
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_retrieval(test: TestQuestion, k: int = 10) -> RetrievalEval:
    retrieved_docs = fetch_context(test.question)
    mrr_scores = [calculate_mrr(keyword, retrieved_docs) for keyword in test.keywords]
    ndcg_scores = [calculate_ndcg(keyword, retrieved_docs, k) for keyword in test.keywords]
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
    keywords_found = sum(1 for score in mrr_scores if score > 0)
    total_keywords = len(test.keywords)
    keyword_coverage = (keywords_found / total_keywords * 100) if total_keywords else 0.0
    return RetrievalEval(
        mrr=avg_mrr,
        ndcg=avg_ndcg,
        keywords_found=keywords_found,
        total_keywords=total_keywords,
        keyword_coverage=keyword_coverage,
    )


def parse_judge_json(raw: str) -> AnswerEval:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    try:
        return AnswerEval.model_validate_json(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise
        return AnswerEval.model_validate_json(text[start : end + 1])


def evaluate_answer(test: TestQuestion, model_choice: str = DEFAULT_MODEL):
    provider, model = MODELS[model_choice]
    client = get_client(provider)
    generated_answer, retrieved_docs = answer_question(
        test.question, client=client, model=model
    )
    judge_messages = [
        {
            "role": "system",
            "content": (
                "You are an expert evaluator. Compare the generated answer to the "
                "reference answer. Reply with JSON only, using keys feedback, "
                "accuracy, completeness, and relevance. Scores are 1 to 5. "
                "Only give 5 for a perfect answer. If the answer is wrong, accuracy must be 1."
            ),
        },
        {
            "role": "user",
            "content": f"""Question:
{test.question}

Generated Answer:
{generated_answer}

Reference Answer:
{test.reference_answer}

Return JSON with:
- feedback: short critique
- accuracy: 1-5
- completeness: 1-5
- relevance: 1-5
""",
        },
    ]
    judge_response = client.chat.completions.create(
        model=model,
        messages=judge_messages,
        response_format={"type": "json_object"},
    )
    answer_eval = parse_judge_json(judge_response.choices[0].message.content or "")
    return answer_eval, generated_answer, retrieved_docs


def evaluate_all_retrieval():
    tests = load_tests()
    total_tests = len(tests)
    for index, test in enumerate(tests):
        result = evaluate_retrieval(test)
        progress = (index + 1) / total_tests if total_tests else 1.0
        yield test, result, progress


def evaluate_all_answers(model_choice: str = DEFAULT_MODEL):
    tests = load_tests()
    total_tests = len(tests)
    for index, test in enumerate(tests):
        result = evaluate_answer(test, model_choice=model_choice)[0]
        progress = (index + 1) / total_tests if total_tests else 1.0
        yield test, result, progress


def run_cli_evaluation(test_number: int):
    tests = load_tests()
    if test_number < 0 or test_number >= len(tests):
        print(f"Error: test_row_number must be between 0 and {len(tests) - 1}")
        sys.exit(1)

    test = tests[test_number]
    print(f"\n{'=' * 80}")
    print(f"Test #{test_number}")
    print(f"{'=' * 80}")
    print(f"Question: {test.question}")
    print(f"Keywords: {test.keywords}")
    print(f"Category: {test.category}")
    print(f"Reference Answer: {test.reference_answer}")

    print(f"\n{'=' * 80}")
    print("Retrieval Evaluation")
    print(f"{'=' * 80}")
    retrieval_result = evaluate_retrieval(test)
    print(f"MRR: {retrieval_result.mrr:.4f}")
    print(f"nDCG: {retrieval_result.ndcg:.4f}")
    print(f"Keywords Found: {retrieval_result.keywords_found}/{retrieval_result.total_keywords}")
    print(f"Keyword Coverage: {retrieval_result.keyword_coverage:.1f}%")

    print(f"\n{'=' * 80}")
    print("Answer Evaluation")
    print(f"{'=' * 80}")
    answer_result, generated_answer, _retrieved_docs = evaluate_answer(test)
    print(f"\nGenerated Answer:\n{generated_answer}")
    print(f"\nFeedback:\n{answer_result.feedback}")
    print("\nScores:")
    print(f"  Accuracy: {answer_result.accuracy:.2f}/5")
    print(f"  Completeness: {answer_result.completeness:.2f}/5")
    print(f"  Relevance: {answer_result.relevance:.2f}/5")
    print(f"\n{'=' * 80}\n")


def main():
    if len(sys.argv) != 2:
        print("Usage: python eval.py <test_row_number>")
        sys.exit(1)
    try:
        test_number = int(sys.argv[1])
    except ValueError:
        print("Error: test_row_number must be an integer")
        sys.exit(1)
    run_cli_evaluation(test_number)


if __name__ == "__main__":
    main()
