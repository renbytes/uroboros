import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error" # Infrastructure error/Timeout
    SKIPPED = "skipped"

class FileArtifact(BaseModel):
    """Represents a file in the codebase."""
    file_path: str
    content: str
    language: str = "python"

class Task(BaseModel):
    """
    A unit of work for the Actor agent. 
    This could be a feature request or a bug report.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    requirements: List[str] = Field(default_factory=list)
    initial_files: List[FileArtifact] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    
    model_config = ConfigDict(frozen=True)

class Patch(BaseModel):
    """A specific modification to a file."""
    file_path: str
    diff: str # Unified diff format
    explanation: str # Chain-of-thought justification for the change

class Solution(BaseModel):
    """The Actor's proposed resolution to a Task."""
    task_id: str
    patches: List[Patch]
    logic_reasoning: str # The 'Reflexion' component

class TestResult(BaseModel):
    """The Arbiter's strict evaluation of a Solution."""
    test_id: str
    status: TestStatus
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    coverage_percent: Optional[float] = None

class Skill(BaseModel):
    """
    Voyager / Genetic Memory Component.
    A re-usable function or strategy extracted from a successful solution.
    """
    name: str
    code: str
    docstring: str
    embedding: Optional[List[float]] = None # Vector representation for RAG
    tags: List[str] = Field(default_factory=list)