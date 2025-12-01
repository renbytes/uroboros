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
from uroboros.core.utils import timer, save_debug_artifact

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
        result = None
        
        try:
            with timer(logger, f"Sandbox Execution {execution_id}"):
                # 1. Initialize Sandbox
                sandbox = await AsyncSandbox.create(api_key=self.api_key)
                
                # 2. Write Files
                logger.debug(f"[{execution_id}] Writing {len(files)} source files")
                for file in files:
                    await self._write_file(sandbox, file)

                logger.debug(f"[{execution_id}] Writing {len(test_files)} test files")
                for file in test_files:
                    await self._write_file(sandbox, file)

                # 3. Install Deps
                if any(f.file_path == "requirements.txt" for f in files):
                    logger.info(f"[{execution_id}] Installing dependencies...")
                    await sandbox.commands.run("pip install -r requirements.txt")

                # 4. Execute Tests
                logger.info(f"[{execution_id}] Running Pytest...")
                cmd = "python -m pytest . -p no:cacheprovider"
                
                # RUN COMMAND SAFELY
                try:
                    proc = await sandbox.commands.run(
                        cmd,
                        timeout=self.timeout_seconds
                    )
                    result = self._parse_process_output(execution_id, proc)

                except Exception as command_error:
                    # Catch E2B CommandExitException (Exit Code != 0)
                    result = self._handle_command_exception(execution_id, command_error)
                
                return result

        except TimeoutError:
            logger.warning(f"[{execution_id}] Execution timed out")
            result = TestResult(
                test_id=execution_id,
                status=TestStatus.ERROR,
                stdout="",
                stderr="Execution Timed Out",
                exit_code=124,
                duration_ms=self.timeout_seconds * 1000
            )
            return result
            
        except Exception as e:
            logger.error(f"[{execution_id}] Sandbox Critical Error: {str(e)}", exc_info=True)
            result = TestResult(
                test_id=execution_id,
                status=TestStatus.ERROR,
                stdout="",
                stderr=f"Infrastructure Error: {str(e)}",
                exit_code=1,
                duration_ms=0
            )
            return result
            
        finally:
            # LOGGING: Save the raw execution results
            if result:
                save_debug_artifact(
                    execution_id, 
                    "sandbox_stdout", 
                    result.stdout, 
                    "log"
                )
                save_debug_artifact(
                    execution_id, 
                    "sandbox_stderr", 
                    result.stderr, 
                    "log"
                )

            # Cleanup
            if sandbox:
                try:
                    await sandbox.kill()
                except Exception as e:
                    logger.warning(f"Failed to kill sandbox {execution_id}: {e}")

    async def _write_file(self, sandbox: AsyncSandbox, file: FileArtifact) -> None:
        """Helper to write a file to the sandbox filesystem."""
        if "/" in file.file_path:
            directory = file.file_path.rsplit("/", 1)[0]
            await sandbox.files.make_dir(directory)
        
        await sandbox.files.write(file.file_path, file.content)

    def _parse_process_output(self, test_id: str, proc_output: Any) -> TestResult:
        """Converts successful process output into TestResult."""
        return TestResult(
            test_id=test_id,
            status=TestStatus.PASSED,
            stdout=getattr(proc_output, 'stdout', ''),
            stderr=getattr(proc_output, 'stderr', ''),
            exit_code=getattr(proc_output, 'exit_code', 0),
            duration_ms=0.0
        )

    def _handle_command_exception(self, test_id: str, error: Any) -> TestResult:
        """
        Extracts output from a failed command exception.
        """
        stdout = getattr(error, 'stdout', "")
        stderr = getattr(error, 'stderr', str(error))
        exit_code = getattr(error, 'exit_code', 1)

        logger.info(f"Command failed with exit code {exit_code}. This is expected for failing tests.")

        return TestResult(
            test_id=test_id,
            status=TestStatus.FAILED,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=0.0
        )