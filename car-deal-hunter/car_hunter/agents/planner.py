from __future__ import annotations

from car_hunter.agents.agent import Agent
from car_hunter.agents.ensemble import EnsembleAgent
from car_hunter.agents.messenger import MessengerAgent
from car_hunter.agents.scanner import ScannerAgent
from car_hunter.config import DEAL_THRESHOLD
from car_hunter.listings import Deal, Opportunity
from car_hunter.vectorstore import CarIndex


class PlanningAgent(Agent):
    name = "Planner"
    color = Agent.GREEN

    def __init__(self, index: CarIndex, threshold: float = DEAL_THRESHOLD):
        self.scanner = ScannerAgent()
        self.ensemble = EnsembleAgent(index)
        self.messenger = MessengerAgent()
        self.threshold = threshold

    def score(self, deal: Deal) -> Opportunity:
        estimate, parts = self.ensemble.price(deal.listing)
        discount = estimate - deal.asking_price
        notes = ", ".join(f"{k}=${v:,.0f}" for k, v in parts.items())
        return Opportunity(deal=deal, estimate=estimate, discount=discount, notes=notes)

    def hunt(self, n: int = 8) -> list[Opportunity]:
        found: list[Opportunity] = []
        for deal in self.scanner.scan(n=n):
            opportunity = self.score(deal)
            if opportunity.discount >= self.threshold:
                self.messenger.notify(opportunity)
                found.append(opportunity)
        found.sort(key=lambda item: item.discount, reverse=True)
        self.log(f"Found {len(found)} deals above ${self.threshold:,.0f} discount")
        return found
