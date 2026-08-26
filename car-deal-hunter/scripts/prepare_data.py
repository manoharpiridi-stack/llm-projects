import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from car_hunter.curator import prepare


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and split Craigslist used-car listings")
    parser.add_argument("--full", action="store_true", help="Keep the full cleaned set instead of the lite sample")
    args = parser.parse_args()
    train, val, test = prepare(lite=not args.full)
    print(f"Saved {len(train):,} train / {len(val):,} val / {len(test):,} test rows to data/")


if __name__ == "__main__":
    main()
