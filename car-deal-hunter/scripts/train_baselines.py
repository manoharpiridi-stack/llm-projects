import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from car_hunter.baselines import median_pricer, predict_rf, train_random_forest
from car_hunter.config import METRICS_PATH
from car_hunter.curator import load_splits
from car_hunter.evaluator import evaluate_predictor, save_metrics
from car_hunter.listings import listings_from_frame


def main() -> None:
    train_df, val_df, test_df = load_splits()
    train = listings_from_frame(train_df)
    test = listings_from_frame(test_df)

    model = train_random_forest(train)
    median = evaluate_predictor(
        lambda item: median_pricer(train, item),
        test,
        title="median_baseline",
        size=min(400, len(test)),
    )
    forest = evaluate_predictor(
        lambda item: predict_rf(model, item),
        test,
        title="random_forest",
        size=min(400, len(test)),
    )
    save_metrics(METRICS_PATH, [median, forest])
    print(json.dumps([median, forest], indent=2))


if __name__ == "__main__":
    main()
