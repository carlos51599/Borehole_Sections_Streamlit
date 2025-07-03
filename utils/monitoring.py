"""Performance monitoring and debugging utilities."""

import time
import logging
import functools
import psutil
import tracemalloc
import traceback
from typing import Any, Callable, Dict
from core.config import AppConfig

logger = logging.getLogger(__name__)


def log_performance(func: Callable) -> Callable:
    """
    Decorator to log function performance.

    Args:
        func: Function to monitor

    Returns:
        Wrapped function with performance logging
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not AppConfig.PROFILE_PERFORMANCE:
            return func(*args, **kwargs)

        start_time = time.time()
        if AppConfig.MONITOR_MEMORY:
            tracemalloc.start()
            start_memory = psutil.Process().memory_info().rss

        try:
            result = func(*args, **kwargs)

            elapsed_time = time.time() - start_time
            logger.info(f"Function {func.__name__} took {elapsed_time:.2f} seconds")

            if AppConfig.MONITOR_MEMORY:
                end_memory = psutil.Process().memory_info().rss
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                memory_diff = end_memory - start_memory
                logger.info(
                    f"Memory change: {memory_diff/1024/1024:.1f}MB, "
                    f"Peak: {peak/1024/1024:.1f}MB"
                )

            return result

        except Exception as e:
            logger.error(
                f"Error in {func.__name__}: {str(e)}\n"
                f"Args: {args}\nKwargs: {kwargs}"
            )
            raise

    return wrapper


def monitor_streamlit_state(key: str, value: Any) -> None:
    """
    Monitor changes to Streamlit session state.

    Args:
        key: State key being modified
        value: New value
    """
    if AppConfig.DEBUG_MODE:
        logger.debug(f"Session state update - {key}: {value}")


def log_error_context(e: Exception, context: str = "") -> None:
    """
    Log detailed error information with context.

    Args:
        e: Exception that occurred
        context: Additional context about where/why the error occurred
    """
    logger.error(
        f"Error: {str(e)}\n"
        f"Context: {context}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )


class PerformanceStats:
    """Track performance statistics during app execution."""

    def __init__(self) -> None:
        """Initialize performance tracking."""
        self.start_time = time.time()
        self.operation_times: Dict[str, float] = {}
        self.error_counts: Dict[str, int] = {}

    def log_operation(self, operation: str, duration: float) -> None:
        """Log the duration of an operation."""
        if operation in self.operation_times:
            self.operation_times[operation] += duration
        else:
            self.operation_times[operation] = duration

    def log_error(self, operation: str) -> None:
        """Log an error occurrence."""
        self.error_counts[operation] = self.error_counts.get(operation, 0) + 1

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        total_time = time.time() - self.start_time
        return {
            "total_runtime": total_time,
            "operation_times": self.operation_times,
            "error_counts": self.error_counts,
            "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024,
        }
