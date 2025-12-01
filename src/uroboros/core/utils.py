import logging
import sys
import json
import time
import re
from pathlib import Path
from typing import Any, Dict, Optional, Generator
from contextlib import contextmanager
from datetime import datetime, timezone

# We delay import of settings to avoid circular imports if config imports utils
# Instead, we will import it inside the function or use a getter pattern if needed.
# For simplicity in this stack, we import normally but keep an eye on config.

class JSONFormatter(logging.Formatter):
    """
    Formatter to output logs as JSON Lines.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if hasattr(record, 'task_id'):
            log_obj['task_id'] = getattr(record, 'task_id')
            
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def setup_logger(
    name: str, 
    log_file: Optional[Path] = None, 
    level: int = logging.INFO,
    json_format: bool = False
) -> logging.Logger:
    """Configures a logger with standard settings."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False 

    if logger.handlers:
        return logger

    stream_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        stream_handler.setFormatter(JSONFormatter())
    else:
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        stream_handler.setFormatter(formatter)
    
    logger.addHandler(stream_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger

@contextmanager
def timer(logger: logging.Logger, operation_name: str) -> Generator[None, None, None]:
    """Context manager to measure execution time."""
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        duration = (end_time - start_time) * 1000 
        logger.info(
            f"{operation_name} completed", 
            extra={"duration_ms": round(duration, 2), "operation": operation_name}
        )

def safe_read_file(path: str | Path) -> str:
    """Safely reads a text file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise IOError(f"Failed to read file at {path}: {str(e)}") from e

def safe_write_file(path: str | Path, content: str) -> None:
    """Safely writes a text file."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        raise IOError(f"Failed to write file at {path}: {str(e)}") from e

def clean_code_block(text: str) -> str:
    """
    Removes Markdown code fences (```python ... ```) to ensure validity.
    """
    pattern = r"```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return max(matches, key=len).strip()
    return text.strip()

# --- NEW DEBUGGING UTILITY ---

def save_debug_artifact(task_id: str, step_name: str, content: str, extension: str = "txt") -> None:
    """
    Saves intermediate artifacts to disk for debugging.
    
    Logic:
    - If DEBUG=true: Saves everything.
    - If DEBUG=false: Only saves if step_name starts with 'final_'.
    """
    # Import inside function to prevent circular import issues with config
    from uroboros.core.config import get_settings
    settings = get_settings()

    is_final = step_name.startswith("final_")
    
    # Policy check
    if not settings.DEBUG and not is_final:
        return

    try:
        # Create directory structure: data/intermediate_debugging/{task_id}/
        base_dir = Path(settings.ROOT_DIR).parent.parent / "data" / "intermediate_debugging" / task_id
        base_dir.mkdir(parents=True, exist_ok=True)

        # Timestamp to order steps: 001_actor_code.py, etc.
        # We use a rough high-res timestamp
        timestamp = datetime.now().strftime("%H%M%S")
        
        filename = f"{timestamp}_{step_name}.{extension}"
        file_path = base_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
    except Exception as e:
        # Never crash the agent because logging failed
        print(f"Failed to save debug artifact: {e}")