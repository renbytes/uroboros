import logging
import re
from typing import Tuple

from uroboros.core.types import TestStatus, TestResult

logger = logging.getLogger(__name__)

class ResultParser:
    """
    Parses raw command output into structured TestResults.
    Crucial for providing granular feedback to the Agent.
    """

    @staticmethod
    def parse_pytest_output(
        test_id: str, 
        exit_code: int, 
        stdout: str, 
        stderr: str, 
        duration_ms: float = 0
    ) -> TestResult:
        """
        Analyzes Pytest output to determine status and extract failure details.
        """
        # 1. Determine Status based on Exit Code
        # Pytest exit codes: 
        # 0: All tests passed
        # 1: Tests were collected and run but some failed
        # 2: Interrupted
        # 3: Internal error
        # 4: Usage error
        # 5: No tests collected
        
        status = TestStatus.ERROR
        if exit_code == 0:
            status = TestStatus.PASSED
        elif exit_code == 1:
            status = TestStatus.FAILED
        elif exit_code == 5:
            status = TestStatus.SKIPPED # No tests found
            
        # 2. Extract Summary (e.g. "3 failed, 1 passed")
        # We look for the final line typical of pytest
        summary_regex = r"==+ (.*) in [\d\.]+s ==+"
        match = re.search(summary_regex, stdout)
        summary = match.group(1) if match else "No summary found"

        # 3. Enhance Error Message
        # If failed, we want to extract the specific assertion error to feed back to the Actor
        cleaned_stderr = stderr
        if status == TestStatus.FAILED:
            # Simple heuristic: Try to find "E   AssertionError" or similar lines in stdout
            # Pytest prints failures to stdout, not stderr usually
            failure_blocks = []
            capture = False
            for line in stdout.splitlines():
                if line.startswith("_________________"): # Start of failure block
                    capture = True
                if capture:
                    failure_blocks.append(line)
            
            if failure_blocks:
                # Append the specific failure details to stderr for the agent to read
                cleaned_stderr = "\n".join(failure_blocks[:50]) # Limit length
            else:
                cleaned_stderr = f"Tests Failed: {summary}"

        return TestResult(
            test_id=test_id,
            status=status,
            stdout=stdout,
            stderr=cleaned_stderr,
            exit_code=exit_code,
            duration_ms=duration_ms
        )

class CommandBuilder:
    """
    Helper to construct shell commands for the sandbox.
    """
    
    @staticmethod
    def build_pytest_cmd(target_dir: str = ".") -> str:
        """
        Constructs a robust pytest command.
        flags:
          -v: verbose (helps parser)
          -p no:cacheprovider: don't write .pytest_cache (permissions issues)
          --tb=short: shorter tracebacks (saves token context)
        """
        return f"pytest {target_dir} -v -p no:cacheprovider --tb=short"