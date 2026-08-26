from __future__ import annotations

import numpy as np
import pandas as pd
from joblib import dump, load
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from car_hunter.config import RF_PATH
from car_hunter.listings import CarListing

CATEGORICAL = ["manufacturer", "condition", "fuel", "transmission", "drive", "type", "state"]
NUMERIC = ["year", "odometer"]


def _frame_from_listings(listings: list[CarListing]) -> pd.DataFrame:
    rows = []
    for item in listings:
        rows.append(
            {
                "manufacturer": item.manufacturer,
                "condition": item.condition or "unknown",
                "fuel": item.fuel or "unknown",
                "transmission": item.transmission or "unknown",
                "drive": item.drive or "unknown",
                "type": item.body_type or "unknown",
                "state": item.state or "unknown",
                "year": item.year,
                "odometer": item.odometer,
                "price": item.price,
            }
        )
    return pd.DataFrame(rows)


def train_random_forest(listings: list[CarListing], n_estimators: int = 120) -> Pipeline:
    df = _frame_from_listings(listings)
    features = CATEGORICAL + NUMERIC
    present_cat = [c for c in CATEGORICAL if c in df.columns]
    model = Pipeline(
        steps=[
            (
                "prep",
                ColumnTransformer(
                    [
                        ("cat", OneHotEncoder(handle_unknown="ignore"), present_cat),
                        ("num", "passthrough", NUMERIC),
                    ]
                ),
            ),
            (
                "rf",
                RandomForestRegressor(
                    n_estimators=n_estimators,
                    random_state=42,
                    n_jobs=-1,
                    min_samples_leaf=2,
                ),
            ),
        ]
    )
    model.fit(df[features], df["price"])
    dump(model, RF_PATH)
    return model


def load_random_forest() -> Pipeline:
    if not RF_PATH.exists():
        raise FileNotFoundError("Run: python scripts/train_baselines.py")
    return load(RF_PATH)


def predict_rf(model: Pipeline, listing: CarListing) -> float:
    df = _frame_from_listings([listing])
    pred = model.predict(df[CATEGORICAL + NUMERIC])[0]
    return float(max(pred, 0.0))


def median_pricer(train: list[CarListing], listing: CarListing) -> float:
    return float(np.median([item.price for item in train]))
