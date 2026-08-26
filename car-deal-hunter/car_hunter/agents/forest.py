from __future__ import annotations

from car_hunter.agents.agent import Agent
from car_hunter.baselines import load_random_forest, predict_rf
from car_hunter.listings import CarListing


class ForestAgent(Agent):
    name = "RandomForest"
    color = Agent.YELLOW

    def __init__(self):
        self.model = load_random_forest()

    def price(self, listing: CarListing) -> float:
        return predict_rf(self.model, listing)
