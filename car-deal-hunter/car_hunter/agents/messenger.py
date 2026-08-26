from __future__ import annotations

import json
from datetime import datetime, timezone

from car_hunter.agents.agent import Agent
from car_hunter.config import ALERTS_PATH
from car_hunter.listings import Opportunity


class MessengerAgent(Agent):
    name = "Messenger"
    color = Agent.GREEN

    def notify(self, opportunity: Opportunity) -> str:
        payload = {
            "time": datetime.now(timezone.utc).isoformat(),
            "title": opportunity.deal.listing.title,
            "asking": opportunity.deal.asking_price,
            "estimate": opportunity.estimate,
            "discount": opportunity.discount,
        }
        ALERTS_PATH.parent.mkdir(exist_ok=True)
        with ALERTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        message = (
            f"Deal: {opportunity.deal.listing.title} asked ${opportunity.deal.asking_price:,.0f}, "
            f"fair value ${opportunity.estimate:,.0f}, discount ${opportunity.discount:,.0f}"
        )
        self.log(message)
        return message
