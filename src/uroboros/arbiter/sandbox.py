import logging
import asyncio
from typing import List, Any
from e2b_code_interpreter import AsyncSandbox

from uroboros.core.interfaces import ArbiterInterface
from uroboros.core.types import (
    FileArtifact, 
    TestResult, 
    TestStatus
)
from uroboros.core.config import get_settings
from uroboros.core.utils import timer

logger = logging.getLogger(__name__)
settings = get_settings()

class E2BArbiter(ArbiterInterface):
    """
    Implementation of the Arbiter using E2B.dev Sandboxes.
    Uses AsyncSandbox from e2b-code-interpreter SDK.
    """

    def __init__(self, timeout_seconds: int = 30):
        self.api_key = settings.E2B_API_KEY.get_secret_value()
        self.timeout_seconds = timeout_seconds

    async def execute(
        self, 
        files: List[FileArtifact], 
        test_files: List[FileArtifact]
    ) -> TestResult:
        """
        Executes the provided code and tests in a fresh microVM.
        """
        
        execution_id = f"exec-{asyncio.get_event_loop().time()}"
        logger.info(f"[{execution_id}] Spawning Sandbox...")
        
        sandbox = None
        try:
            with timer(logger, f"Sandbox Execution {execution_id}"):
                # CHANGED: Use factory method .create() and await it
                # We cannot use 'async with' directly on the factory awaitable
                sandbox = await AsyncSandbox.create(api_key=self.api_key)
                
                # 1. Write Source Code
                logger.debug(f"[{execution_id}] Writing {len(files)} source files")
                for file in files:
                    await self._write_file(sandbox, file)

                # 2. Write Test Files
                logger.debug(f"[{execution_id}] Writing {len(test_files)} test files")
                for file in test_files:
                    await self._write_file(sandbox, file)

                # 3. Check for dependencies
                if any(f.file_path == "requirements.txt" for f in files):
                    logger.info(f"[{execution_id}] Installing dependencies...")
                    await sandbox.commands.run("pip install -r requirements.txt")

                # 4. Execute Tests
                logger.info(f"[{execution_id}] Running Pytest...")
                cmd = "pytest . -p no:cacheprovider"
                
                # e2b-code-interpreter v1+ uses .commands.run
                proc = await sandbox.commands.run(
                    cmd,
                    timeout=self.timeout_seconds
                )

                # 5. Parse Results
                return self._parse_process_output(execution_id, proc)

        except TimeoutError:
            logger.warning(f"[{execution_id}] Execution timed out after {self.timeout_seconds}s")
            return TestResult(
                test_id=execution_id,
                status=TestStatus.ERROR,
                stdout="",
                stderr="Execution Timed Out",
                exit_code=124,
                duration_ms=self.timeout_seconds * 1000
            )
        except Exception as e:
            logger.error(f"[{execution_id}] Sandbox Error: {str(e)}", exc_info=True)
            return TestResult(
                test_id=execution_id,
                status=TestStatus.ERROR,
                stdout="",
                stderr=f"Infrastructure Error: {str(e)}",
                exit_code=1,
                duration_ms=0
            )
        finally:
            # CHANGED: Manually kill the sandbox in the finally block
            if sandbox:
                try:
                    await sandbox.kill()
                except Exception as e:
                    logger.warning(f"Failed to kill sandbox {execution_id}: {e}")

    async def _write_file(self, sandbox: AsyncSandbox, file: FileArtifact) -> None:
        """Helper to write a file to the sandbox filesystem."""
        # SDK v1 uses .files instead of .filesystem
        if "/" in file.file_path:
            directory = file.file_path.rsplit("/", 1)[0]
            await sandbox.files.make_dir(directory)
        
        await sandbox.files.write(file.file_path, file.content)

    def _parse_process_output(self, test_id: str, proc_output: Any) -> TestResult:
        """
        Converts E2B process output into our internal TestResult.
        """
        if proc_output.exit_code == 0:
            status = TestStatus.PASSED
        elif proc_output.exit_code == 1:
            status = TestStatus.FAILED
        else:
            status = TestStatus.ERROR

        return TestResult(
            test_id=test_id,
            status=status,
            stdout=proc_output.stdout,
            stderr=proc_output.stderr,
            exit_code=proc_output.exit_code,
            duration_ms=0.0
        )