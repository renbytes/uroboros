import logging
from typing import List
from pydantic import BaseModel, Field

from uroboros.core.types import FileArtifact, Task
from uroboros.llm.client import LLMClient
from uroboros.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ReproScript(BaseModel):
    """Structured output for the reproduction script."""
    filename: str = Field(..., description="Name of the test file, e.g., test_repro_issue_12.py")
    code: str = Field(..., description="The full Python code for the test case.")
    expected_failure_reason: str

class ReproductionAgent:
    """
    Translates natural language bug reports into executable regression tests.
    """

    def __init__(self):
        self.llm = LLMClient(model_name=settings.ADVERSARY_MODEL)

    async def create_reproduction_case(self, task: Task) -> List[FileArtifact]:
        """
        Generates a test file that FAILS on the current codebase (reproducing the bug)
        and SHOULD PASS once the bug is fixed.
        """
        logger.info(f"Generating reproduction script for Task {task.id}...")

        # Flatten context
        code_context = "\n".join(
            [f"--- {f.file_path} ---\n{f.content}" for f in task.initial_files]
        )

        system_prompt = """
You are a QA Automation Engineer.
Your goal is to write a MINIMAL REPRODUCTION SCRIPT for a reported bug.

RULES:
1. The script must be a valid `pytest` file.
2. It must attempt to exercise the bug described.
3. It must ASSERT the CORRECT behavior (which is currently failing).
4. Do not just assert False. Assert what *should* happen if the code were correct.
"""

        user_prompt = f"""
### Bug Description:
{task.description}

### Current Codebase:
{code_context}

### Output:
Write a pytest reproduction file.
"""

        try:
            repro = await self.llm.chat_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=ReproScript
            )

            logger.info(f"Generated reproduction case: {repro.filename}")

            return [
                FileArtifact(
                    file_path=f"tests/repro/{repro.filename}",
                    content=repro.code,
                    language="python"
                )
            ]

        except Exception as e:
            logger.error(f"Failed to generate reproduction script: {e}")
            # Fallback: Return empty list, system will proceed without specific repro
            return []