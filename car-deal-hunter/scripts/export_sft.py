import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from car_hunter.config import DATA_DIR
from car_hunter.curator import load_splits
from car_hunter.listings import listings_from_frame


def main() -> None:
    train_df, val_df, test_df = load_splits()
    DATA_DIR.mkdir(exist_ok=True)
    for name, frame in [("train", train_df), ("val", val_df), ("test", test_df)]:
        path = DATA_DIR / f"{name}_sft.jsonl"
        listings = listings_from_frame(frame)
        with path.open("w", encoding="utf-8") as handle:
            for item in listings:
                handle.write(json.dumps({"text": item.prompt}) + "\n")
        print(f"Wrote {len(listings):,} rows to {path}")


if __name__ == "__main__":
    main()
