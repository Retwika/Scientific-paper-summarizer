"""
Logger configuration for the summarizing agent.

Provides structured logging with rich formatting for console output.
"""

import logging
from pathlib import Path
from rich.logging import RichHandler
from rich.console import Console


def setup_logger(name: str = "summarizer", level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with rich console output.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Rich handler for beautiful console output
    console = Console()
    handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_path=False
    )
    
    handler.setLevel(level)
    formatter = logging.Formatter(
        "%(message)s",
        datefmt="[%X]"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


# Default logger instance
logger = setup_logger()
