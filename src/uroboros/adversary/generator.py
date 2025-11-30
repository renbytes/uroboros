import logging
from typing import List
from pydantic import BaseModel

from uroboros.core.interfaces import AdversaryInterface
from uroboros.core.types import (
    Task, 
    Solution, 
    FileArtifact, 
    TaskStatus
)
from uroboros.core.config import get_settings
from uroboros.llm.client import LLMClient

logger = logging.getLogger(__name__)
settings = get_settings()

class AdversarialTestPlan(BaseModel):
    """Internal model for the LLM to structure its attack plan."""
    test_files: List[FileArtifact]
    explanation: str

class InfCodeAdversary(AdversaryInterface):
    """
    The Critic Agent.
    Implements Generative Adversarial Software Testing (GAST).
    """

    def __init__(self):
        self.llm = LLMClient(model_name=settings.ADVERSARY_MODEL)

    async def generate_curriculum(self, difficulty_level: int) -> Task:
        """
        Generates a new coding challenge based on difficulty.
        Difficulty 1: Simple string manipulation.
        Difficulty 10: Async race conditions, memory leaks, security exploits.
        """
        logger.info(f"Generating curriculum with difficulty {difficulty_level}...")

        system_prompt = f"""
        You are the Taskmaster for an AI Software Engineer.
        Your goal is to generate a coding challenge that pushes the agent's limits.
        Current Difficulty Level: {difficulty_level}/10.

        - For Level 1-3: Focus on basic algorithms and data structures.
        - For Level 4-7: Focus on system design, APIs, and multi-file refactoring.
        - For Level 8-10: Focus on concurrency, security vulnerabilities (SQLi, XSS), and optimization.
        """

        user_prompt = "Generate a new Task. Return it as a structured object."

        # We reuse the Task model for the response to ensure strict typing
        task = await self.llm.chat_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=Task
        )
        
        # Ensure status is pending
        return Task(
            id=task.id,
            description=task.description,
            requirements=task.requirements,
            initial_files=task.initial_files,
            status=TaskStatus.PENDING
        )

    async def generate_adversarial_tests(self, solution: Solution) -> List[FileArtifact]:
        """
        The GAST Loop.
        Analyzes the proposed solution and generates 'Killer Tests'.
        """
        logger.info(f"Generating adversarial tests for Task {solution.task_id}...")

        # Convert patches to string for analysis
        patch_content = "\n".join([p.diff for p in solution.patches])
        
        system_prompt = """
        You are a Red Team Security Engineer and QA Lead.
        Your goal is to BREAK the provided code solution.

        1. Analyze the 'Code Patches' for logic errors, off-by-one errors, or unhandled edge cases.
        2. Write a Python test file (using `pytest`) that targets these weaknesses.
        3. Your test MUST be valid Python code.
        4. Your test MUST assert correct behavior (truth), not just run.
        """

        user_prompt = f"""
        ### Logic Reasoning provided by Builder:
        {solution.logic_reasoning}

        ### Code Patches:
        {patch_content}

        Generate a suite of adversarial tests now.
        """

        plan = await self.llm.chat_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=AdversarialTestPlan
        )

        logger.info(f"Generated {len(plan.test_files)} adversarial test files.")
        return plan.test_files