from __future__ import annotations

from car_hunter.agents.agent import Agent
from car_hunter.agents.forest import ForestAgent
from car_hunter.agents.rag import RagAgent
from car_hunter.agents.specialist import SpecialistAgent
from car_hunter.listings import CarListing
from car_hunter.vectorstore import CarIndex


class EnsembleAgent(Agent):
    name = "Ensemble"
    color = Agent.MAGENTA

    def __init__(self, index: CarIndex):
        self.forest = ForestAgent()
        self.rag = RagAgent(index)
        self.specialist = SpecialistAgent()

    def price(self, listing: CarListing) -> tuple[float, dict[str, float]]:
        parts: dict[str, float] = {}
        parts["random_forest"] = self.forest.price(listing)
        parts["rag"] = self.rag.price(listing)
        specialist = self.specialist.price(listing)
        if specialist is not None and specialist > 0:
            parts["specialist"] = specialist

        if len(parts) == 3:
            estimate = 0.5 * parts["random_forest"] + 0.3 * parts["rag"] + 0.2 * parts["specialist"]
        else:
            estimate = 0.65 * parts["random_forest"] + 0.35 * parts["rag"]
        self.log(f"Estimate ${estimate:,.0f} from {parts}")
        return float(estimate), parts
