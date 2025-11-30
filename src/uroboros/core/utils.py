import logging
import sys
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Generator
from contextlib import contextmanager
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    """
    Formatter to output logs as JSON Lines.
    Essential for the Evolver agent to parse execution history programmatically.
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
        
        # Include extra attributes passed via logging (e.g., logging.info(..., extra={'task_id': '123'}))
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
    """
    Configures a logger with standard settings.
    
    Args:
        name: Name of the logger (usually __name__).
        log_file: Optional path to write logs to disk.
        level: Logging threshold.
        json_format: If True, outputs logs as JSON lines (for machine consumption).
    
    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False # Prevent double logging if attached to root

    if logger.handlers:
        return logger

    # Console Handler
    stream_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        stream_handler.setFormatter(JSONFormatter())
    else:
        # Standard readable format for humans
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        stream_handler.setFormatter(formatter)
    
    logger.addHandler(stream_handler)

    # File Handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        # Always use JSON for file logs so the Evolver can read them
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger

@contextmanager
def timer(logger: logging.Logger, operation_name: str) -> Generator[None, None, None]:
    """
    Context manager to measure and log execution time of blocks.
    
    Usage:
        with timer(logger, "Running Tests"):
            run_tests()
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        duration = (end_time - start_time) * 1000 # ms
        logger.info(
            f"{operation_name} completed", 
            extra={"duration_ms": round(duration, 2), "operation": operation_name}
        )

def safe_read_file(path: str | Path) -> str:
    """Safely reads a text file, ensuring UTF-8 encoding."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise IOError(f"Failed to read file at {path}: {str(e)}") from e

def safe_write_file(path: str | Path, content: str) -> None:
    """Safely writes a text file, creating parent directories if needed."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        raise IOError(f"Failed to write file at {path}: {str(e)}") from e
