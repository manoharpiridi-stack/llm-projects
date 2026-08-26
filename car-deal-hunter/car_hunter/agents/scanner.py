from __future__ import annotations

from car_hunter.agents.agent import Agent
from car_hunter.curator import load_splits
from car_hunter.listings import CarListing, Deal, listing_from_row


class ScannerAgent(Agent):
    """Uses held-out test listings as a market feed (no scraping, no paid APIs)."""

    name = "Scanner"
    color = Agent.CYAN

    def __init__(self):
        _, _, test = load_splits()
        self.feed = test.sample(frac=1, random_state=7).reset_index(drop=True)
        self.cursor = 0

    def scan(self, n: int = 8) -> list[Deal]:
        if self.cursor >= len(self.feed):
            self.cursor = 0
        chunk = self.feed.iloc[self.cursor : self.cursor + n]
        self.cursor += n
        deals = []
        for row in chunk.to_dict(orient="records"):
            listing: CarListing = listing_from_row(row)
            deals.append(Deal(listing=listing, asking_price=listing.price))
        self.log(f"Scanned {len(deals)} listings from the test-set market feed")
        return deals
