import logging
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from uroboros.core.config import get_settings
from uroboros.core.utils import safe_read_file, safe_write_file
from uroboros.evolver.meta import MetaPrompter
from uroboros.arbiter.metrics import RunMetrics

logger = logging.getLogger(__name__)
settings = get_settings()

class PromptVersion(BaseModel):
    """Represents a specific snapshot of the agent's system prompt."""
    version_id: int
    content: str
    created_at: float = Field(default_factory=time.time)
    parent_version: Optional[int] = None
    change_summary: str = "Initial Version"
    
    # Performance Stats
    runs: int = 0
    successes: int = 0
    avg_success_rate: float = 0.0

class PromptOptimizer:
    """
    Manages the lifecycle of the System Prompt.
    Decides WHEN to evolve (trigger Meta-Prompting) based on metrics.
    """

    def __init__(self, persistence_path: str = "data/prompt_history.json"):
        self.persistence_path = Path(settings.ROOT_DIR).parent.parent / persistence_path
        self.meta_prompter = MetaPrompter()
        
        self.history: List[PromptVersion] = []
        self.current_version_id: int = 0
        
        # Thresholds
        self.evolution_threshold_runs = 5 # Minimum runs before considering evolution
        self.evolution_threshold_rate = 0.6 # If success rate < 60%, evolve.

        self._load_history()

    @property
    def current_prompt(self) -> str:
        """Returns the active system prompt."""
        if not self.history:
            return self._get_default_prompt()
        return self.history[-1].content

    def record_run(self, success: bool) -> None:
        """
        Updates statistics for the current prompt version.
        """
        if not self.history:
            self._initialize_history()

        current = self.history[-1]
        current.runs += 1
        if success:
            current.successes += 1
        
        current.avg_success_rate = current.successes / current.runs
        self._save_history()

    async def step(self, recent_failures: List[str]) -> bool:
        """
        The Optimization Step.
        Checks if evolution is necessary, and if so, performs it.
        
        Returns:
            True if prompt was updated.
        """
        if not self.history:
            return False

        current = self.history[-1]

        # 1. Check if we have enough data
        if current.runs < self.evolution_threshold_runs:
            return False

        # 2. Check if performance is acceptable
        if current.avg_success_rate >= self.evolution_threshold_rate:
            logger.info(f"Prompt Performance Good ({current.avg_success_rate:.2f}). No evolution needed.")
            return False

        logger.info(f"📉 Performance degraded ({current.avg_success_rate:.2f} < {self.evolution_threshold_rate}). Triggering Evolution.")

        # 3. Evolve
        evolution = await self.meta_prompter.evolve_system_prompt(
            current_prompt=current.content,
            failure_history=recent_failures
        )

        # 4. Register New Version
        new_version = PromptVersion(
            version_id=self.current_version_id + 1,
            content=evolution.optimized_prompt,
            parent_version=current.version_id,
            change_summary=evolution.change_summary
        )
        
        self.history.append(new_version)
        self.current_version_id += 1
        self._save_history()
        
        logger.info(f"🧬 Prompt Evolved to v{new_version.version_id}")
        return True

    def _get_default_prompt(self) -> str:
        """Fallback prompt if no history exists."""
        return """You are Uroboros, an elite Autonomous Software Engineer.
Your goal is to solve the user's task by modifying the codebase.
Analyze requirements, check your memory for skills, and write robust code."""

    def _initialize_history(self) -> None:
        """Creates the initial genesis prompt."""
        genesis = PromptVersion(
            version_id=0,
            content=self._get_default_prompt()
        )
        self.history.append(genesis)
        self._save_history()

    def _load_history(self) -> None:
        """Loads prompt lineage from disk."""
        if self.persistence_path.exists():
            try:
                data = json.loads(safe_read_file(self.persistence_path))
                self.history = [PromptVersion(**item) for item in data]
                if self.history:
                    self.current_version_id = self.history[-1].version_id
            except Exception as e:
                logger.error(f"Failed to load prompt history: {e}")
                self._initialize_history()
        else:
            self._initialize_history()

    def _save_history(self) -> None:
        """Persists prompt lineage to disk."""
        try:
            data = [v.model_dump() for v in self.history]
            safe_write_file(self.persistence_path, json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save prompt history: {e}")