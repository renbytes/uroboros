import ast
import inspect
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class IntrospectionEngine:
    """
    Provides capabilities for the agent to analyze its own source code
    and runtime state (The 'Gödel' component).
    """

    @staticmethod
    def get_class_source(obj: Any) -> str:
        """Retrieves the source code of a specific class or object."""
        try:
            return inspect.getsource(obj)
        except Exception as e:
            logger.error(f"Failed to inspect source: {e}")
            return ""

    @staticmethod
    def analyze_complexity(source_code: str) -> Dict[str, Any]:
        """
        Parses the AST to calculate basic complexity metrics.
        Used by the agent to determine if code needs refactoring.
        """
        try:
            tree = ast.parse(source_code)
            
            # Count functions and classes
            func_count = sum(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
            class_count = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
            
            # Rough Cyclomatic Complexity (counting branches)
            branches = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                    branches += 1
            
            return {
                "functions": func_count,
                "classes": class_count,
                "cyclomatic_complexity_proxy": branches
            }
        except SyntaxError as e:
            logger.error(f"Syntax error during introspection: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_runtime_stack() -> str:
        """
        Captures the current stack trace. 
        Useful for debugging self-modifications.
        """
        return "\n".join([str(f) for f in inspect.stack()])