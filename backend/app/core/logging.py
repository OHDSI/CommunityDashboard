"""Logging configuration for the application."""

import logging
import sys
from typing import Optional
from pythonjsonlogger import jsonlogger
from app.config import settings

# Create logger
logger = logging.getLogger("ohdsi")

def setup_logging(
    level: str = "INFO",
    json_logs: bool = True,
    log_file: Optional[str] = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format
        log_file: Optional log file path
    """
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create formatter
    if json_logs:
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False

# Structured logging utilities
def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    **kwargs
) -> None:
    """Log HTTP request details."""
    logger.info(
        "http_request",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            **kwargs
        }
    )

def log_error(
    error_type: str,
    error_message: str,
    traceback: Optional[str] = None,
    **kwargs
) -> None:
    """Log error details."""
    logger.error(
        "application_error",
        extra={
            "error_type": error_type,
            "error_message": error_message,
            "traceback": traceback,
            **kwargs
        }
    )

def log_metric(
    metric_name: str,
    value: float,
    unit: str = "count",
    **tags
) -> None:
    """Log application metrics."""
    logger.info(
        "application_metric",
        extra={
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "tags": tags
        }
    )

def log_ml_classification(
    article_id: str,
    score: float,
    predicted_class: str,
    processing_time_ms: float,
    **kwargs
) -> None:
    """Log ML classification results."""
    logger.info(
        "ml_classification",
        extra={
            "article_id": article_id,
            "score": score,
            "predicted_class": predicted_class,
            "processing_time_ms": processing_time_ms,
            **kwargs
        }
    )

# Initialize logging on module import
setup_logging(
    level=settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else "INFO",
    json_logs=settings.ENVIRONMENT == "production" if hasattr(settings, 'ENVIRONMENT') else False
)