import logging
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
from uroboros.core.utils import safe_read_file, save_debug_artifact
from uroboros.llm.client import LLMClient

logger = logging.getLogger(__name__)
settings = get_settings()

class UroborosActor(ActorInterface):
    """
    The Builder Agent. 
    Combines 'Voyager' (Skill Retrieval) and 'Gödel' (Self-Modification).
    """

    def __init__(self, memory: MemoryInterface):
        self.memory = memory
        self.llm = LLMClient(model_name=settings.ACTOR_MODEL)
        self.source_path = Path(__file__)

    async def solve(self, task: Task) -> Solution:
        """
        Solves a software engineering task.
        """
        logger.info(f"Actor received task: {task.id}")

        # 1. Voyager Step: Retrieve Skills
        relevant_skills = await self.memory.retrieve_relevant_skills(
            query=task.description, 
            limit=3
        )
        
        # Format skills for prompt
        skill_context = "\n".join(
            [f"- {s.name}: {s.docstring}\nCODE:\n{s.code}" for s in relevant_skills]
        ) if relevant_skills else "No relevant past skills found."

        # LOGGING: Save the context we retrieved
        save_debug_artifact(
            task.id, 
            "actor_skills_retrieved", 
            skill_context, 
            "txt"
        )

        # 2. Build Context
        file_context = "\n".join(
            [f"--- {f.file_path} ---\n{f.content}\n" for f in task.initial_files]
        )

        system_prompt = f"""
You are Ouroboros, an elite Autonomous Software Engineer.
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
3. Create specific patches. Provide the FULL FILE CONTENT in the diff field.
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
        solution = await self.llm.chat_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=Solution
        )
        
        solution.task_id = task.id
        
        # LOGGING: Save the solution details
        save_debug_artifact(
            task.id, 
            "actor_reasoning", 
            solution.logic_reasoning, 
            "md"
        )
        
        for idx, patch in enumerate(solution.patches):
            save_debug_artifact(
                task.id,
                f"actor_generated_code_{idx}_{Path(patch.file_path).name}",
                patch.diff,
                "py"
            )
        
        logger.info(f"Generated solution with {len(solution.patches)} patches.")
        return solution

    async def introspect(self) -> None:
        """The Gödel Mechanism."""
        logger.info("Initiating Gödel Introspection...")

        my_source_code = safe_read_file(self.source_path)

        system_prompt = """
You are a Meta-Architect analyzing an AI Agent's source code.
Your goal is to identify inefficiencies, rigid prompts, or lack of robustness.
"""
        user_prompt = f"""
Here is the source code for the 'UroborosActor' class:

```python
{my_source_code}

        Analyze the solve method. Suggest a specific code modification to improve the prompt engineering or the retrieval logic. Return the suggestion as a structured patch or detailed advice. 

        """
        suggestion = await self.llm.chat(
                system_prompt=system_prompt, 
                user_prompt=user_prompt
            )

        save_debug_artifact("system_introspect", "godel_reflection", suggestion, "md")
        
        logger.info(f"Gödel Reflection Result:\n{suggestion}")
