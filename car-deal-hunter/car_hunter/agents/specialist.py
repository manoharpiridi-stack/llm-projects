from __future__ import annotations

from pathlib import Path

from car_hunter.agents.agent import Agent
from car_hunter.config import PREFIX, QUESTION, SPECIALIST_ADAPTER
from car_hunter.evaluator import parse_price
from car_hunter.listings import CarListing
from car_hunter.llm import LLMUnavailable, available, complete


class SpecialistAgent(Agent):
    """Fine-tuned QLoRA model if present; otherwise a local Ollama pricing prompt."""

    name = "Specialist"
    color = Agent.RED

    def __init__(self):
        self.adapter = Path(SPECIALIST_ADAPTER)
        self.peft_ready = (self.adapter / "adapter_config.json").exists()
        self.pipeline = None
        if self.peft_ready:
            self.log(f"Loading local QLoRA adapter from {self.adapter}")
            self.pipeline = self._load_peft()
        elif available():
            self.log("No QLoRA adapter found; using local LLM as specialist")
        else:
            self.log("Specialist unavailable (no adapter, no LLM)")

    def _load_peft(self):
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        config_text = (self.adapter / "adapter_config.json").read_text(encoding="utf-8")
        import json

        base_name = json.loads(config_text)["base_model_name_or_path"]
        tokenizer = AutoTokenizer.from_pretrained(base_name)
        tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(base_name, device_map="auto")
        model = PeftModel.from_pretrained(model, str(self.adapter))
        model.eval()
        return tokenizer, model

    def price(self, listing: CarListing) -> float | None:
        prompt = f"{QUESTION}\n\n{listing.description}\n\n{PREFIX}"
        if self.pipeline:
            tokenizer, model = self.pipeline
            import torch

            inputs = tokenizer.encode(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = inputs.to("cuda")
            with torch.no_grad():
                outputs = model.generate(inputs, max_new_tokens=8)
            text = tokenizer.decode(outputs[0])
            return parse_price(text.split(PREFIX, 1)[-1])
        if not available():
            return None
        try:
            text = complete(
                prompt,
                system="You estimate used-car prices in US dollars. Reply with a number only.",
            )
            return parse_price(text)
        except LLMUnavailable:
            return None
