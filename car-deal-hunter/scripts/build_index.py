import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from car_hunter.curator import load_splits
from car_hunter.listings import listings_from_frame
from car_hunter.vectorstore import CarIndex


def main() -> None:
    train_df, _, _ = load_splits()
    listings = listings_from_frame(train_df)
    index = CarIndex()
    index.build(listings)
    print(f"Indexed {index.collection.count():,} listings into data/chroma")


if __name__ == "__main__":
    main()
