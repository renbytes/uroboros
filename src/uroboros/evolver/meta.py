import logging
from typing import List
from pydantic import BaseModel, Field

from uroboros.llm.client import LLMClient
from uroboros.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class PromptEvolution(BaseModel):
    """Structured output for the optimized prompt."""
    analysis: str = Field(..., description="Why the previous prompt failed.")
    optimized_prompt: str = Field(..., description="The new, improved system prompt.")
    change_summary: str = Field(..., description="Brief summary of changes made.")

class MetaPrompter:
    """
    The Evolutionary Engine.
    Refines the Actor's instructions based on empirical failure data.
    """

    def __init__(self):
        # The Evolver usually requires the smartest model available
        self.llm = LLMClient(model_name=settings.EVOLVER_MODEL)

    async def evolve_system_prompt(
        self, 
        current_prompt: str, 
        failure_history: List[str]
    ) -> PromptEvolution:
        """
        Analyzes a list of failures and rewrites the system prompt to prevent them.
        
        Args:
            current_prompt: The text currently defining the Actor's persona.
            failure_history: A list of error messages / stderr from the Arbiter.
            
        Returns:
            A PromptEvolution object containing the new prompt.
        """
        logger.info(f"Evolving system prompt based on {len(failure_history)} failures...")

        # Compress history if too long to save tokens
        context_str = "\n".join(failure_history[:5]) 

        system_instruction = """
You are a Prompt Engineer and AI Psychologist.
Your goal is to optimize the 'System Prompt' of an AI Code Agent.

The Agent is failing specific tasks. You must:
1. Analyze the FAILURE LOGS to identify the root cause (e.g., "Agent forgets to import modules", "Agent ignores edge cases").
2. Diagnose why the CURRENT PROMPT failed to prevent this behavior.
3. Rewrite the CURRENT PROMPT to explicitly address these weaknesses.
4. Keep the prompt concise but strict.
"""

        user_instruction = f"""
### CURRENT SYSTEM PROMPT:
{current_prompt}

### RECENT FAILURE LOGS:
{context_str}

### INSTRUCTIONS:
Rewrite the system prompt to fix these recurring errors.
"""

        try:
            evolution = await self.llm.chat_structured(
                system_prompt=system_instruction,
                user_prompt=user_instruction,
                response_model=PromptEvolution
            )
            
            logger.info(f"Prompt Evolved: {evolution.change_summary}")
            return evolution

        except Exception as e:
            logger.error(f"Meta-Prompting failed: {e}")
            # Fallback: Return original prompt wrapped in object
            return PromptEvolution(
                analysis="Error during evolution",
                optimized_prompt=current_prompt,
                change_summary="None (Error)"
            )
            