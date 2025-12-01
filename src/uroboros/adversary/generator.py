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
from uroboros.core.utils import save_debug_artifact
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

        task_data = await self.llm.chat_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=Task
        )
        
        # LOGGING: Save the generated task
        save_debug_artifact(
            task_data.id, 
            "adversary_curriculum_task", 
            f"Description: {task_data.description}\nRequirements: {task_data.requirements}", 
            "txt"
        )
        
        return Task(
            id=task_data.id,
            description=task_data.description,
            requirements=task_data.requirements,
            initial_files=task_data.initial_files,
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
3. CRITICAL: The 'content' field of the test file must be PURE PYTHON CODE. 
   - Do NOT include markdown fences.
   - Do NOT include conversational text.

GUIDELINES FOR ATTACKS:
- Focus on LOGIC errors (e.g. is_prime(1) returns True).
- Focus on BOUNDARY errors (e.g. negative numbers, 0, large primes).
- DO NOT obsess over Python type semantics (e.g. whether 'True' is an int). 
  - Assume standard Python typing rules apply unless the code explicitly claims strictness.
  - Do not penalize for accepting 'numpy.int64' if it works mathematically.
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

        # LOGGING: Save the attack plan
        save_debug_artifact(
            solution.task_id, 
            "adversary_attack_plan", 
            plan.explanation, 
            "md"
        )

        # LOGGING: Save the test files
        for idx, test_file in enumerate(plan.test_files):
            # Clean filename for saving
            safe_name = test_file.file_path.replace("/", "_").replace("\\", "_")
            save_debug_artifact(
                solution.task_id,
                f"adversary_test_code_{idx}_{safe_name}",
                test_file.content,
                "py"
            )

        logger.info(f"Generated {len(plan.test_files)} adversarial test files.")
        return plan.test_files