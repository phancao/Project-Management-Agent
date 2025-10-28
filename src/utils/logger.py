"""
Structured logging system for Project Management Agent
Provides colored console output, JSON logging, and performance tracking
"""

import logging
import sys
import json
import time
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
import os


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for console"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Get a configured logger instance
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level.upper()))
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Create formatter
    console_format = ColoredFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # File handler for structured logs
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # JSON formatter for structured logs
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            if record.exc_info:
                log_entry['exception'] = self.formatException(record.exc_info)
            
            return json.dumps(log_entry, ensure_ascii=False)
    
    file_handler.setFormatter(JSONFormatter())
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


def setup_logging_from_env():
    """Setup logging from environment variables"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    
    if debug_mode:
        log_level = 'DEBUG'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    return get_logger('project_management_agent.config')


def log_api_call(func):
    """Decorator to log API calls with performance metrics"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        logger.info(f"API call started: {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"API call completed: {func.__name__} (took {duration:.2f}s)")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"API call failed: {func.__name__} (took {duration:.2f}s) - {str(e)}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        logger.info(f"API call started: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"API call completed: {func.__name__} (took {duration:.2f}s)")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"API call failed: {func.__name__} (took {duration:.2f}s) - {str(e)}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


# Import asyncio for the decorator
import asyncio


