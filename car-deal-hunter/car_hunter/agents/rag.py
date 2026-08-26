from __future__ import annotations

import numpy as np

from car_hunter.agents.agent import Agent
from car_hunter.evaluator import parse_price
from car_hunter.listings import CarListing
from car_hunter.llm import LLMUnavailable, available, complete
from car_hunter.vectorstore import CarIndex


class RagAgent(Agent):
    name = "RAG"
    color = Agent.BLUE

    def __init__(self, index: CarIndex):
        self.index = index

    def price(self, listing: CarListing) -> float:
        docs, prices = self.index.query(listing.description, n_results=5)
        if not prices:
            return 0.0
        knn = float(np.mean(prices))
        if not available():
            self.log("No LLM; returning kNN mean of similar listings")
            return knn

        examples = "\n\n".join(
            f"Similar listing:\n{doc}\nSold/asked at ${price:,.0f}"
            for doc, price in zip(docs, prices)
        )
        prompt = (
            "Estimate the fair US dollar price of this used car. "
            "Reply with a number only.\n\n"
            f"Target car:\n{listing.description}\n\n"
            f"{examples}\n\n"
            f"kNN mean of similars is ${knn:,.0f}."
        )
        try:
            return parse_price(complete(prompt, system="Used-car pricing expert."))
        except LLMUnavailable:
            return knn
