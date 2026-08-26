from __future__ import annotations

from typing import Any

import pandas as pd
from pydantic import BaseModel

from car_hunter.config import PREFIX, QUESTION


class CarListing(BaseModel):
    title: str
    manufacturer: str
    year: int
    price: float
    odometer: float
    description: str
    prompt: str | None = None
    condition: str | None = None
    fuel: str | None = None
    transmission: str | None = None
    drive: str | None = None
    body_type: str | None = None
    state: str | None = None

    def make_prompt(self) -> str:
        self.prompt = f"{QUESTION}\n\n{self.description}\n\n{PREFIX}{round(self.price)}.00"
        return self.prompt

    def test_prompt(self) -> str:
        if not self.prompt:
            self.make_prompt()
        return self.prompt.split(PREFIX)[0] + PREFIX

    def __repr__(self) -> str:
        return f"<{self.title} = ${self.price:,.0f}>"


class Deal(BaseModel):
    listing: CarListing
    asking_price: float


class Opportunity(BaseModel):
    deal: Deal
    estimate: float
    discount: float
    notes: str = ""


def listing_text_from_row(row: dict[str, Any] | pd.Series) -> str:
    year = int(row["year"])
    make = str(row["manufacturer"]).replace("_", " ").title()
    miles = int(float(row["odometer"]))
    lines = [
        f"{year} {make} used vehicle for sale.",
        f"Mileage: {miles:,} miles.",
    ]
    labels = [
        ("Condition", "condition"),
        ("Fuel", "fuel"),
        ("Transmission", "transmission"),
        ("Drivetrain", "drive"),
        ("Body type", "type"),
        ("Cylinders", "cylinders"),
        ("Color", "paint_color"),
        ("Title status", "title_status"),
        ("Listed in", "state"),
    ]
    for label, key in labels:
        value = row.get(key) if isinstance(row, dict) else row.get(key)
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text and text.lower() not in {"unknown", "nan", "none"}:
            lines.append(f"{label}: {text}.")
    return " ".join(lines)


def listing_from_row(row: dict[str, Any] | pd.Series) -> CarListing:
    year = int(row["year"])
    make = str(row["manufacturer"]).replace("_", " ").title()
    title = f"{year} {make}"
    item = CarListing(
        title=title,
        manufacturer=make.lower(),
        year=year,
        price=float(row["price"]),
        odometer=float(row["odometer"]),
        description=listing_text_from_row(row),
        condition=_opt(row, "condition"),
        fuel=_opt(row, "fuel"),
        transmission=_opt(row, "transmission"),
        drive=_opt(row, "drive"),
        body_type=_opt(row, "type"),
        state=_opt(row, "state"),
    )
    item.make_prompt()
    return item


def _opt(row: dict[str, Any] | pd.Series, key: str) -> str | None:
    value = row.get(key) if isinstance(row, dict) else row.get(key)
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text if text and text.lower() not in {"unknown", "nan"} else None


def listings_from_frame(df: pd.DataFrame) -> list[CarListing]:
    return [listing_from_row(row) for row in df.to_dict(orient="records")]
