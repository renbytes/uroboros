from abc import ABC, abstractmethod
from typing import List, Dict, Any

from uroboros.core.types import (
    Task, 
    Solution, 
    TestResult, 
    Skill, 
    FileArtifact
)

class ActorInterface(ABC):
    """
    The 'Builder' Agent (Live-SWE + Gödel).
    Responsible for generating code patches and self-improvement.
    """

    @abstractmethod
    async def solve(self, task: Task) -> Solution:
        """
        Analyzes a task and produces a code solution.
        Includes the 'Plan -> Act -> Observe' loop.
        """
        pass

    @abstractmethod
    async def introspect(self) -> None:
        """
        The Gödel mechanism. 
        Reads its own source code and applies patches if performance degrades.
        """
        pass

class AdversaryInterface(ABC):
    """
    The 'Critic' Agent (InfCode + GAST).
    Responsible for generating tasks and adversarial tests.
    """

    @abstractmethod
    async def generate_curriculum(self, difficulty_level: int) -> Task:
        """
        Generates a new task/problem at the specified difficulty.
        Used for open-ended learning (Auto-Curriculum).
        """
        pass

    @abstractmethod
    async def generate_adversarial_tests(self, solution: Solution) -> List[FileArtifact]:
        """
        Analyzes a proposed solution and generates test cases specifically
        designed to break it (e.g., edge cases, boundary conditions).
        """
        pass

class ArbiterInterface(ABC):
    """
    The 'Judge' (Execution Environment).
    Responsible for running code in a secure sandbox.
    """

    @abstractmethod
    async def execute(self, files: List[FileArtifact], test_files: List[FileArtifact]) -> TestResult:
        """
        Spins up a sandbox (e.g., E2B/Firecracker), writes the files, 
        runs the tests, and returns the strict result.
        """
        pass

class MemoryInterface(ABC):
    """
    The 'Long-Term Memory' (Voyager).
    Responsible for storing and retrieving learned skills.
    """

    @abstractmethod
    async def retrieve_relevant_skills(self, query: str, limit: int = 3) -> List[Skill]:
        """
        Semantic search for skills related to the current problem.
        """
        pass

    @abstractmethod
    async def store_skill(self, skill: Skill) -> None:
        """
        Indexes a new verified skill into the vector database.
        """
        pass
