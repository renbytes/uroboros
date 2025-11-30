import logging
from typing import List, Optional
from pydantic import BaseModel

from uroboros.core.types import Skill
from uroboros.llm.client import LLMClient
from uroboros.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ReRankResult(BaseModel):
    """The output of the re-ranking process."""
    selected_skill_names: List[str]
    reasoning: str

class RetrievalStrategy:
    """
    Implements advanced retrieval patterns like Reranking and Hybrid Search.
    Helps filter out 'hallucinated' matches from the vector DB.
    """

    def __init__(self):
        # We use the Actor model for re-ranking as it needs code understanding
        self.llm = LLMClient(model_name=settings.ACTOR_MODEL)

    async def rerank(self, query: str, candidates: List[Skill], top_k: int = 3) -> List[Skill]:
        """
        Uses an LLM to filter and sort candidate skills based on relevance to the query.
        
        Args:
            query: The current task description.
            candidates: A larger list (e.g., 10) retrieved from VectorDB.
            top_k: How many to return after filtering.
            
        Returns:
            The subset of skills that are truly relevant.
        """
        if not candidates:
            return []
            
        # If we have few candidates, no need to waste tokens re-ranking
        if len(candidates) <= top_k:
            return candidates

        logger.info(f"Re-ranking {len(candidates)} skills for query: '{query[:50]}...'")

        # Create a condensed context for the LLM
        candidate_context = "\n".join(
            [f"ID: {s.name}\nDocstring: {s.docstring}\n" for s in candidates]
        )

        system_prompt = """
You are a Senior Engineer acting as a Retrieval System.
Your goal is to select the most relevant code skills from a list to help solve a specific task.
Discard irrelevant skills.
"""

        user_prompt = f"""
### TASK:
{query}

### CANDIDATE SKILLS:
{candidate_context}

### INSTRUCTIONS:
Select the top {top_k} skills that are most likely to help solve the task.
Return the list of Skill IDs.
"""

        try:
            result = await self.llm.chat_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=ReRankResult
            )

            # Filter the original list based on LLM selection
            selected_map = {name: True for name in result.selected_skill_names}
            final_skills = [s for s in candidates if s.name in selected_map]
            
            # If LLM returned garbage IDs, fallback to original top_k
            if not final_skills:
                logger.warning("Re-ranking returned no valid matches, falling back to vector order.")
                return candidates[:top_k]

            logger.info(f"Re-ranking selected {len(final_skills)} skills. Logic: {result.reasoning[:100]}...")
            return final_skills[:top_k]

        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            # Fallback to vector similarity order
            return candidates[:top_k]

    @staticmethod
    def format_for_prompt(skills: List[Skill]) -> str:
        """
        Helper to format skills into a string for injection into the Actor's context window.
        """
        if not skills:
            return "No relevant skills found."
            
        output = []
        for i, skill in enumerate(skills, 1):
            block = f"""
[Skill #{i}: {skill.name}]
Description: {skill.docstring}
Code:
{skill.code}
"""
            output.append(block)
        
        return "\n".join(output)