import asyncio
import logging
import argparse
import sys
from typing import Optional

from uroboros.core.config import get_settings
from uroboros.core.utils import setup_logger, timer
from uroboros.core.types import Task, TaskStatus, TestStatus, Skill
from uroboros.actor.agent import uroborosActor
from uroboros.adversary.generator import InfCodeAdversary
from uroboros.arbiter.sandbox import E2BArbiter
from uroboros.memory.skills import VoyagerMemory

# Setup Root Logger
logger = setup_logger("uroboros", json_format=False)
settings = get_settings()

class uroborosEngine:
    """
    The Main Loop Orchestrator.
    Manages the lifecycle: Generate -> Solve -> Attack -> Verify -> Evolve.
    """

    def __init__(self):
        self.memory = VoyagerMemory()
        self.actor = uroborosActor(memory=self.memory)
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

        # --- PHASE 2: The Loop (Solve & Verify) ---
        success = False
        attempts = 0
        
        # We maintain a 'conversation history' or 'feedback buffer' here
        # In a real implementation, this would be appended to the Task requirements
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
            # We must convert patches to actual files for the sandbox
            # For this MVP, we assume the patches contain the full file content or valid diffs
            # In a full implementation, we'd need a 'PatchApplier' utility.
            # Here we naively map patches to FileArtifacts for simplicity.
            source_files = [
                # In reality, you apply the diff to the original file. 
                # This assumes 'diff' is the full file content for MVP.
                type(task.initial_files[0])(file_path=p.file_path, content=p.diff, language="python") 
                for p in solution.patches
            ]

            result = await self.arbiter.execute(
                files=source_files, 
                test_files=adversarial_tests
            )

            logger.info(f"Arbiter Verdict: {result.status.upper()}")
            
            if result.status == TestStatus.PASSED:
                success = True
                logger.info("✅ Solution Verified against Adversarial Tests.")
                
                # --- PHASE 3: Evolution (Memory Consolidation) ---
                # Save the winning move to the Skill Library
                new_skill = Skill(
                    name=f"skill_{task.id[:8]}",
                    code=solution.patches[0].diff, # Naive: saving the first patch as the skill
                    docstring=f"Solution for: {task.description}",
                    tags=["verified", "auto-generated"]
                )
                await self.memory.store_skill(new_skill)
                
            else:
                logger.warning(f"❌ Verification Failed.\nStderr: {result.stderr[:200]}...")
                previous_feedback = f"Test Failed with stderr: {result.stderr}"

        if success:
            logger.info("🏆 Cycle Complete: SUCCESS")
        else:
            logger.error("💀 Cycle Complete: FAILED (Max Retries Exceeded)")

async def main():
    parser = argparse.ArgumentParser(description="uroboros: Adversarial Software Agent")
    parser.add_argument("--task", type=str, help="Specific task description to solve")
    parser.add_argument("--loop", action="store_true", help="Run in continuous autonomous mode")
    args = parser.parse_args()

    engine = uroborosEngine()

    if args.loop:
        logger.info("Starting Infinite Autonomous Loop...")
        while True:
            try:
                await engine.run_cycle()
                await asyncio.sleep(5) # Breathe
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                await asyncio.sleep(10)
    else:
        # Single run
        task_desc = args.task or "Write a Python function to calculate Fibonacci numbers recursively with memoization."
        await engine.run_cycle(task_desc)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down uroboros.")
        sys.exit(0)
