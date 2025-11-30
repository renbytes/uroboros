import logging
import json
import tiktoken
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field

from uroboros.core.config import get_settings
from uroboros.core.utils import safe_read_file, safe_write_file

logger = logging.getLogger(__name__)
settings = get_settings()

# Current OpenAI Pricing (as of late 2024/2025 estimates)
# Structure: {model_name: {input_price_per_1k, output_price_per_1k}}
PRICING_TABLE = {
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    # Fallback default
    "default": {"input": 0.01, "output": 0.03}
}

class SessionCost(BaseModel):
    """Tracks usage for the current execution session."""
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0

class CostManager:
    """
    Singleton-style manager to track LLM spend.
    Persists data to disk to maintain budget caps across restarts.
    """
    
    def __init__(self, persistence_path: str = "data/cost_ledger.json"):
        self.persistence_path = Path(settings.ROOT_DIR).parent.parent / persistence_path
        self.session = SessionCost()
        self.budget_limit_usd = 50.00 # Hard cap for safety
        
        # Cache encoders to avoid reloading tiktoken files constantly
        self._encoders: Dict[str, Any] = {}
        
        self._load_ledger()

    def count_tokens(self, text: str, model: str = "gpt-4-turbo") -> int:
        """
        Accurately counts tokens for a given string and model.
        """
        try:
            if model not in self._encoders:
                try:
                    encoding = tiktoken.encoding_for_model(model)
                except KeyError:
                    encoding = tiktoken.get_encoding("cl100k_base")
                self._encoders[model] = encoding
            
            return len(self._encoders[model].encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}. Defaulting to len/4 approximation.")
            return len(text) // 4

    def update_usage(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """
        Updates the internal ledger and checks budget.
        """
        prices = PRICING_TABLE.get(model, PRICING_TABLE["default"])
        
        input_cost = (input_tokens / 1000) * prices["input"]
        output_cost = (output_tokens / 1000) * prices["output"]
        total_cost = input_cost + output_cost

        self.session.input_tokens += input_tokens
        self.session.output_tokens += output_tokens
        self.session.total_tokens += (input_tokens + output_tokens)
        self.session.total_cost_usd += total_cost

        # Log periodically
        if self.session.total_tokens % 10000 < (input_tokens + output_tokens): 
            # Simple heuristic to log roughly every 10k tokens
            logger.info(f"💰 Current Session Cost: ${self.session.total_cost_usd:.4f}")

        self._save_ledger()
        self._check_budget()

    def _check_budget(self) -> None:
        """
        Raises an error if budget is exceeded to stop the agent.
        """
        if self.session.total_cost_usd >= self.budget_limit_usd:
            msg = f"💸 BUDGET EXCEEDED: ${self.session.total_cost_usd:.2f} >= ${self.budget_limit_usd:.2f}"
            logger.critical(msg)
            raise RuntimeError(msg)

    def _load_ledger(self) -> None:
        """Loads previous cost data."""
        if self.persistence_path.exists():
            try:
                data = json.loads(safe_read_file(self.persistence_path))
                # We add previous run costs to current session tracking for safety
                # In a real app, you might want separate 'lifetime' vs 'session' tracking
                self.session.total_cost_usd = data.get("total_cost_usd", 0.0)
            except Exception as e:
                logger.error(f"Failed to load cost ledger: {e}")

    def _save_ledger(self) -> None:
        """Persists cost data."""
        try:
            safe_write_file(self.persistence_path, self.session.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to save cost ledger: {e}")