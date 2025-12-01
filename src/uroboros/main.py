import asyncio
import logging
import argparse
import sys
from typing import Optional

from uroboros.core.config import get_settings
from uroboros.core.utils import setup_logger, timer, save_debug_artifact, clean_code_block
from uroboros.core.types import Task, TaskStatus, TestStatus, Skill, FileArtifact
from uroboros.actor.agent import UroborosActor
from uroboros.adversary.generator import InfCodeAdversary
from uroboros.arbiter.sandbox import E2BArbiter
from uroboros.memory.skills import VoyagerMemory

# Setup Root Logger
logger = setup_logger("uroboros", json_format=False)
settings = get_settings()

class OuroborosEngine:
    """
    The Main Loop Orchestrator.
    Manages the lifecycle: Generate -> Solve -> Attack -> Verify -> Evolve.
    """

    def __init__(self):
        self.memory = VoyagerMemory()
        self.actor = UroborosActor(memory=self.memory)
        self.adversary = InfCodeAdversary()
        self.arbiter = E2BArbiter()
        self.max_retries = 3

    async def run_cycle(self, task_description: Optional[str] = None):
        """
        Executes one full evolutionary cycle.
        """
        # --- PHASE 1: Task Generation ---
        if task_description:
            # User provided task
            task = Task(description=task_description)
            logger.info(f"🚀 Starting User Task: {task.id}")
        else:
            # Autonomous Curriculum (Adversary generates task)
            task = await self.adversary.generate_curriculum(difficulty_level=5)
            logger.info(f"🚀 Starting Autonomous Task: {task.id}")

        # LOGGING: Save the Task Definition
        save_debug_artifact(
            task.id,
            "task_definition",
            f"Description: {task.description}\nRequirements: {task.requirements}",
            "txt"
        )

        # --- PHASE 2: The Loop (Solve & Verify) ---
        success = False
        attempts = 0
        previous_feedback = ""

        while attempts < self.max_retries and not success:
            attempts += 1
            logger.info(f"\n--- Attempt {attempts}/{self.max_retries} ---")
            
            # If we failed previously, append the feedback to the task
            if previous_feedback:
                task = task.model_copy(update={
                    "description": f"{task.description}\n\nPREVIOUS FAILURE FEEDBACK:\n{previous_feedback}"
                })

            # A. Actor Solves
            with timer(logger, "Actor Solving"):
                solution = await self.actor.solve(task)

            # B. Adversary Attacks (Generates Killer Tests)
            with timer(logger, "Adversary Attacking"):
                adversarial_tests = await self.adversary.generate_adversarial_tests(solution)

            # C. Arbiter Verifies
            # 1. Clean and Prepare Source Files
            source_files = [
                FileArtifact(
                    file_path=p.file_path, 
                    content=clean_code_block(p.diff), 
                    language="python"
                ) 
                for p in solution.patches
            ]

            # 2. Clean and Prepare Test Files
            clean_test_files = [
                FileArtifact(
                    file_path=t.file_path,
                    content=clean_code_block(t.content),
                    language="python"
                )
                for t in adversarial_tests
            ]

            result = await self.arbiter.execute(
                files=source_files, 
                test_files=clean_test_files
            )

            logger.info(f"Arbiter Verdict: {result.status.upper()}")
            
            if result.status == TestStatus.PASSED:
                success = True
                logger.info("✅ Solution Verified against Adversarial Tests.")
                
                # --- PHASE 3: Evolution (Memory Consolidation) ---
                
                # 1. Save to Memory (Vector DB)
                final_code = source_files[0].content
                new_skill = Skill(
                    name=f"skill_{task.id[:8]}",
                    code=final_code, 
                    docstring=f"Solution for: {task.description}",
                    tags=["verified", "auto-generated"]
                )
                await self.memory.store_skill(new_skill)

                # 2. LOGGING: Save Final Artifacts (Always saved, even if DEBUG=False)
                save_debug_artifact(task.id, "final_solution_code", final_code, "py")
                save_debug_artifact(task.id, "final_solution_skill", new_skill.model_dump_json(indent=2), "json")
                
            else:
                # FAILURE HANDLING
                logger.warning(f"❌ Verification Failed.")
                
                # Combine stdout and stderr for the feedback loop
                # Pytest output is mostly in stdout
                feedback_content = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                previous_feedback = f"Test Failed. Output:\n{feedback_content}"
                
                # LOGGING: Save the FULL failure log (stdout + stderr)
                save_debug_artifact(
                    task.id, 
                    f"attempt_{attempts}_failure_log", 
                    feedback_content, 
                    "log"
                )

        if success:
            logger.info("🏆 Cycle Complete: SUCCESS")
        else:
            logger.error("💀 Cycle Complete: FAILED (Max Retries Exceeded)")
            # LOGGING: Save final failure state
            save_debug_artifact(task.id, "final_status", "FAILED", "txt")

async def main():
    parser = argparse.ArgumentParser(description="Ouroboros: Adversarial Software Agent")
    parser.add_argument("--task", type=str, help="Specific task description to solve")
    parser.add_argument("--loop", action="store_true", help="Run in continuous autonomous mode")
    args = parser.parse_args()

    engine = OuroborosEngine()

    if args.loop:
        logger.info("Starting Infinite Autonomous Loop...")
        while True:
            try:
                await engine.run_cycle()
                await asyncio.sleep(5) 
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Loop Error: {e}", exc_info=True)
                await asyncio.sleep(10)
    else:
        # Single run
        task_desc = args.task or "Write a Python function to calculate Fibonacci numbers recursively with memoization."
        await engine.run_cycle(task_desc)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Ouroboros.")
        sys.exit(0)