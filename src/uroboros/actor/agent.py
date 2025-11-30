import logging
import inspect
from pathlib import Path
from typing import List, Optional

from uroboros.core.interfaces import ActorInterface, MemoryInterface
from uroboros.core.types import (
    Task, 
    Solution, 
    FileArtifact, 
    Patch
)
from uroboros.core.config import get_settings
from uroboros.core.utils import safe_read_file
from uroboros.llm.client import LLMClient

logger = logging.getLogger(__name__)
settings = get_settings()

class uroborosActor(ActorInterface):
    """
    The Builder Agent. 
    Combines 'Voyager' (Skill Retrieval) and 'Gödel' (Self-Modification).
    """

    def __init__(self, memory: MemoryInterface):
        self.memory = memory
        self.llm = LLMClient(model_name=settings.ACTOR_MODEL)
        # Store path to self for introspection
        self.source_path = Path(__file__)

    async def solve(self, task: Task) -> Solution:
        """
        Solves a software engineering task.
        
        1. Query Memory for relevant skills/past solutions.
        2. Construct context with Task + Files + Skills.
        3. Generate Solution using LLM.
        """
        logger.info(f"Actor received task: {task.id}")

        # 1. Voyager Step: Retrieve Skills
        # We search for skills using the task description as the query
        relevant_skills = await self.memory.retrieve_relevant_skills(
            query=task.description, 
            limit=3
        )
        skill_context = "\n".join(
            [f"- {s.name}: {s.docstring}" for s in relevant_skills]
        ) if relevant_skills else "No relevant past skills found."

        # 2. Build Context
        # Flatten file artifacts into a readable string
        file_context = "\n".join(
            [f"--- {f.file_path} ---\n{f.content}\n" for f in task.initial_files]
        )

        system_prompt = f"""
You are uroboros, an elite Autonomous Software Engineer.
Your goal is to solve the user's task by modifying the codebase.

### Capabilities:
- You analyze the provided code and requirements.
- You generate precise Python code patches.
- You utilize your Long-Term Memory (Skills) to avoid repeating mistakes.

### Memory (Learned Skills):
{skill_context}

### Instructions:
1. Analyze the 'Task Description' and 'Code Context'.
2. Explain your reasoning (Chain of Thought).
3. Create specific patches. Use standard unified diff format if possible, 
   but for this structured output, provide the full content or clear replacement blocks.
"""

        user_prompt = f"""
### Task:
{task.description}

### Requirements:
{", ".join(task.requirements)}

### Current Codebase:
{file_context}

Provide your solution now.
"""

        # 3. Generate Solution
        # We enforce the strict 'Solution' Pydantic model
        solution = await self.llm.chat_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=Solution
        )
        
        # Inject the task ID back into the solution object (LLM might miss it)
        solution.task_id = task.id
        
        logger.info(f"Generated solution with {len(solution.patches)} patches.")
        return solution

    async def introspect(self) -> None:
        """
        The Gödel Mechanism.
        The agent reads its own source code and reflects on how to improve its 'solve' logic.
        
        Note: In this implementation, we log the improvement suggestion.
        In the full 'Ad Infinitum' version, this would trigger a self-patching routine.
        """
        logger.info("Initiating Gödel Introspection...")

        # 1. Read Self
        my_source_code = safe_read_file(self.source_path)

        # 2. Reflect
        system_prompt = """
        You are a Meta-Architect analyzing an AI Agent's source code.
        Your goal is to identify inefficiencies, rigid prompts, or lack of robustness in the agent's logic.
        """
        user_prompt = f"""
        Here is the source code for the 'uroborosActor' class:

        ```python
        {my_source_code}
        ```

        Analyze the solve method. Suggest a specific code modification to improve the prompt engineering or the retrieval logic. Return the suggestion as a structured patch or detailed advice. 

        """
        suggestion = await self.llm.chat(
                system_prompt=system_prompt, 
                user_prompt=user_prompt
            )

        logger.info(f"Gödel Reflection Result:\n{suggestion}")
