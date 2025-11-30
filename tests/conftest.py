import sys
import os
import pytest
import asyncio
from typing import Generator

# Ensure 'src' is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Configure asyncio for pytest
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Creates an instance of the default event loop for the test session.
    Required for pytest-asyncio.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_task():
    """Returns a dummy Task object for unit testing."""
    from uroboros.core.types import Task
    return Task(
        description="Fix the divide by zero error",
        requirements=["Must handle zero input", "Return None on error"]
    )
