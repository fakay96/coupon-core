"""Logging utilities for the Coupon Core project."""

import logging
import json
import traceback
from typing import Any, Dict, Optional
from functools import wraps
from datetime import datetime

# Get loggers for each app
auth_logger = logging.getLogger('authentication')
geo_logger = logging.getLogger('geodiscounts')
celery_logger = logging.getLogger('celery')

class StructuredLogger:
    """
    A utility class for structured logging across the application.
    
    This class provides methods for logging with consistent structure and
    additional context information.
    """
    
    @staticmethod
    def _format_context(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format context data for logging."""
        if not context:
            return {}
        return {k: str(v) for k, v in context.items()}
    
    @staticmethod
    def _log_event(
        logger: logging.Logger,
        level: int,
        message: str,
        event_type: str,
        context: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ) -> None:
        """
        Log an event with structured data.
        
        Args:
            logger: The logger instance to use
            level: Logging level (e.g., logging.INFO)
            message: The main log message
            event_type: Type of event being logged
            context: Additional context data
            error: Exception object if logging an error
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'message': message,
            'context': StructuredLogger._format_context(context)
        }
        
        if error:
            log_data.update({
                'error': {
                    'type': error.__class__.__name__,
                    'message': str(error),
                    'traceback': traceback.format_exc()
                }
            })
            
        logger.log(level, json.dumps(log_data))
    
    @classmethod
    def info(
        cls,
        logger: logging.Logger,
        message: str,
        event_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an info level event."""
        cls._log_event(logger, logging.INFO, message, event_type, context)
    
    @classmethod
    def error(
        cls,
        logger: logging.Logger,
        message: str,
        event_type: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an error level event."""
        cls._log_event(logger, logging.ERROR, message, event_type, context, error)
    
    @classmethod
    def warning(
        cls,
        logger: logging.Logger,
        message: str,
        event_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a warning level event."""
        cls._log_event(logger, logging.WARNING, message, event_type, context)
    
    @classmethod
    def debug(
        cls,
        logger: logging.Logger,
        message: str,
        event_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a debug level event."""
        cls._log_event(logger, logging.DEBUG, message, event_type, context)

def log_execution(logger: logging.Logger, event_type: str):
    """
    Decorator for logging function execution.
    
    Args:
        logger: The logger instance to use
        event_type: Type of event being logged
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log function entry
            StructuredLogger.info(
                logger,
                f"Entering {func.__name__}",
                event_type,
                {'args': str(args), 'kwargs': str(kwargs)}
            )
            
            try:
                result = func(*args, **kwargs)
                # Log successful execution
                StructuredLogger.info(
                    logger,
                    f"Successfully completed {func.__name__}",
                    event_type,
                    {'result': str(result)}
                )
                return result
            except Exception as e:
                # Log error
                StructuredLogger.error(
                    logger,
                    f"Error in {func.__name__}",
                    event_type,
                    e,
                    {'args': str(args), 'kwargs': str(kwargs)}
                )
                raise
                
        return wrapper
    return decorator

# Create logger instances for each app
auth_structured_logger = StructuredLogger()
geo_structured_logger = StructuredLogger()
celery_structured_logger = StructuredLogger() 