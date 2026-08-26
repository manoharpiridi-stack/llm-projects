from __future__ import annotations

import json
import math
import re
from itertools import accumulate

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from car_hunter.listings import CarListing


def parse_price(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("$", "").replace(",", "")
    match = re.search(r"[-+]?\d*\.\d+|\d+", text)
    return float(match.group()) if match else 0.0


def evaluate_predictions(
    truths: list[float],
    guesses: list[float],
    title: str = "model",
) -> dict:
    mae = float(mean_absolute_error(truths, guesses))
    rmse = float(math.sqrt(mean_squared_error(truths, guesses)))
    r2 = float(r2_score(truths, guesses))
    return {
        "title": title,
        "n": len(truths),
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "r2": round(r2, 4),
    }


def evaluate_predictor(
    predictor,
    listings: list[CarListing],
    title: str | None = None,
    size: int | None = None,
) -> dict:
    sample = listings[: size or len(listings)]
    guesses = [parse_price(predictor(item)) for item in sample]
    truths = [item.price for item in sample]
    name = title or getattr(predictor, "__name__", "model")
    return evaluate_predictions(truths, guesses, name)


def running_mae(errors: list[float]) -> list[float]:
    totals = list(accumulate(errors))
    return [total / i for i, total in enumerate(totals, start=1)]


def save_metrics(path, rows: list[dict]) -> None:
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def metrics_table(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)
