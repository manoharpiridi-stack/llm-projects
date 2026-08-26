from __future__ import annotations

import pandas as pd
from datasets import load_dataset
from sklearn.model_selection import train_test_split

from car_hunter.config import (
    HF_DATASET,
    LITE_TEST,
    LITE_TRAIN,
    LITE_VAL,
    MAX_ODOMETER,
    MAX_PRICE,
    MIN_PRICE,
    MIN_YEAR,
    TEST_PATH,
    TRAIN_PATH,
    VAL_PATH,
)


NEEDED = [
    "price",
    "year",
    "manufacturer",
    "odometer",
    "condition",
    "fuel",
    "transmission",
    "drive",
    "type",
    "cylinders",
    "paint_color",
    "title_status",
    "state",
    "car_age",
]


def load_raw() -> pd.DataFrame:
    ds = load_dataset(HF_DATASET, split="train")
    return ds.to_pandas()


def clean(df: pd.DataFrame) -> pd.DataFrame:
    keep = [c for c in NEEDED if c in df.columns]
    out = df[keep].copy()
    out["price"] = pd.to_numeric(out["price"], errors="coerce")
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["odometer"] = pd.to_numeric(out["odometer"], errors="coerce")
    out = out.dropna(subset=["price", "year", "manufacturer", "odometer"])
    out = out[
        (out["price"] >= MIN_PRICE)
        & (out["price"] <= MAX_PRICE)
        & (out["year"] >= MIN_YEAR)
        & (out["odometer"] >= 0)
        & (out["odometer"] <= MAX_ODOMETER)
    ]
    out["manufacturer"] = out["manufacturer"].astype(str).str.lower().str.strip()
    out = out[out["manufacturer"].ne("unknown")]
    if "car_age" not in out.columns:
        out["car_age"] = 2026 - out["year"]
    return out.drop_duplicates().reset_index(drop=True)


def split_and_save(df: pd.DataFrame, lite: bool = True, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train, temp = train_test_split(df, test_size=0.2, random_state=seed)
    val, test = train_test_split(temp, test_size=0.5, random_state=seed)

    if lite:
        train = train.sample(n=min(LITE_TRAIN, len(train)), random_state=seed)
        val = val.sample(n=min(LITE_VAL, len(val)), random_state=seed)
        test = test.sample(n=min(LITE_TEST, len(test)), random_state=seed)

    TRAIN_PATH.parent.mkdir(exist_ok=True)
    train.to_parquet(TRAIN_PATH, index=False)
    val.to_parquet(VAL_PATH, index=False)
    test.to_parquet(TEST_PATH, index=False)
    return train, val, test


def load_splits() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not TRAIN_PATH.exists():
        raise FileNotFoundError("Run: python scripts/prepare_data.py")
    return (
        pd.read_parquet(TRAIN_PATH),
        pd.read_parquet(VAL_PATH),
        pd.read_parquet(TEST_PATH),
    )


def prepare(lite: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = load_raw()
    cleaned = clean(raw)
    return split_and_save(cleaned, lite=lite)
