import logging
import ast
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field

from uroboros.core.types import FileArtifact
from uroboros.llm.client import LLMClient
from uroboros.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ToolSpec(BaseModel):
    """Structured output for the LLM when generating a tool."""
    filename: str = Field(..., description="e.g., check_links.py")
    code: str
    usage_example: str

class ToolSynthesizer:
    """
    Generates ad-hoc Python tools on the fly.
    Allows the agent to build its own utilities for specific tasks.
    """

    def __init__(self):
        # We use the Actor model for tool synthesis as it requires coding capability
        self.llm = LLMClient(model_name=settings.ACTOR_MODEL)

    async def synthesize(self, need_description: str, context: str = "") -> Optional[FileArtifact]:
        """
        Creates a new tool based on a specific need.
        
        Args:
            need_description: e.g., "I need to parse a custom binary log format."
            context: Optional code or data snippet to understand the format.
            
        Returns:
            A FileArtifact containing the executable Python script, or None if validation fails.
        """
        logger.info(f"Synthesizing tool for: {need_description}")

        system_prompt = """
You are a Toolsmith. Your job is to write standalone Python scripts to help an AI agent solve engineering tasks.
The agent operates in a Linux sandbox.

GUIDELINES:
1. The script must be self-contained (no external pip dependencies unless standard).
2. It should accept input via command-line arguments (argparse) or stdin.
3. It must print results to stdout.
4. It must be robust and handle errors gracefully.
"""

        user_prompt = f"""
### NEED:
{need_description}

### CONTEXT:
{context}

Generate a Python script to solve this specific problem.
"""

        try:
            tool_spec = await self.llm.chat_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=ToolSpec
            )

            # 1. Validate Syntax
            if not self._validate_syntax(tool_spec.code):
                logger.error("Synthesized tool had syntax errors.")
                return None

            # 2. Return Artifact
            return FileArtifact(
                file_path=f"tools/{tool_spec.filename}",
                content=tool_spec.code,
                language="python"
            )

        except Exception as e:
            logger.error(f"Tool synthesis failed: {e}")
            return None

    def _validate_syntax(self, code: str) -> bool:
        """Checks if the generated code is valid Python."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.error(f"Syntax Validation Error: {e}")
            return False