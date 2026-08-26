from __future__ import annotations

import logging
import sys

from car_hunter.agents.planner import PlanningAgent
from car_hunter.listings import CarListing
from car_hunter.vectorstore import CarIndex


def init_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class DealHunter:
    def __init__(self):
        init_logging()
        self.index = CarIndex()
        if self.index.collection.count() == 0:
            raise FileNotFoundError("Chroma is empty. Run: python scripts/build_index.py")
        self.planner = PlanningAgent(self.index)

    def estimate_listing(self, listing: CarListing) -> tuple[float, dict]:
        return self.planner.ensemble.price(listing)

    def hunt(self, n: int = 8):
        return self.planner.hunt(n=n)
