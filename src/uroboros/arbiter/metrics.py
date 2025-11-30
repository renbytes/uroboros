import logging
from typing import List
from pydantic import BaseModel

from uroboros.core.types import TestResult, TestStatus

logger = logging.getLogger(__name__)

class RunMetrics(BaseModel):
    """
    Aggregated statistics for a specific execution cycle.
    """
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    success_rate: float
    avg_duration_ms: float

class MetricsEngine:
    """
    Calculates Success Metrics (KPIs) from raw TestResults.
    """

    @staticmethod
    def compute_run_metrics(results: List[TestResult]) -> RunMetrics:
        """
        Aggregates a list of individual test results into a high-level report.
        """
        total = len(results)
        if total == 0:
            return RunMetrics(
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                error_tests=0,
                success_rate=0.0,
                avg_duration_ms=0.0
            )

        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        # Calculate Average Duration
        total_duration = sum(r.duration_ms for r in results)
        avg_duration = total_duration / total

        # Calculate Success Rate (0.0 to 1.0)
        rate = passed / total if total > 0 else 0.0

        return RunMetrics(
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            error_tests=errors,
            success_rate=round(rate, 4),
            avg_duration_ms=round(avg_duration, 2)
        )

    @staticmethod
    def evaluate_pass_at_k(solutions: List[bool], k: int = 1) -> float:
        """
        Calculates Pass@k metric.
        This represents the probability that at least one of the top 'k' generated solutions is correct.
        
        Formula: 1 - Combination(n-c, k) / Combination(n, k)
        For simple single-stream loops, this simplifies to binary success.
        """
        # TODO: Implement full combinatorial logic for Pass@k if multiple solutions are generated.
        # TODO: make more robust
        # MVP Implementation: Just return the success rate of the batch
        if not solutions:
            return 0.0
        
        # If any solution in the batch passed, we consider it a success for Pass@k context
        if any(solutions):
            return 1.0
        return 0.0