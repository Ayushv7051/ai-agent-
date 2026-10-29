"""
Structured Logging with Credential Redaction for Ayush AI.
Logs to logs/agent.log and standard output.
"""

import logging
import re
from logging.handlers import RotatingFileHandler
from config import LOG_FILE

# Regular expressions for identifying potential secrets
SECRET_PATTERNS = [
    r'(?i)(api[_-]?key|secret|password|token|auth|bearer)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
    r'(?i)(ghp_[A-Za-z0-9_]{36})',
    r'(?i)(sk-[A-Za-z0-9-_]{20,})',
    r'(?i)(\b[0-9]{8,10}:[a-zA-Z0-9_-]{35}\b)',  # Telegram token pattern
]

class RedactingFormatter(logging.Formatter):
    """Formatter that masks sensitive keys and tokens from log messages."""
    
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        redacted = original
        for pattern in SECRET_PATTERNS:
            def _mask(match):
                full = match.group(0)
                if match.lastindex and match.lastindex >= 2:
                    secret_val = match.group(2)
                    if len(secret_val) > 4:
                        masked_val = secret_val[:2] + "****" + secret_val[-2:]
                    else:
                        masked_val = "****"
                    return full.replace(secret_val, masked_val)
                elif match.lastindex == 1:
                    secret_val = match.group(1)
                    if len(secret_val) > 6:
                        masked_val = secret_val[:3] + "****" + secret_val[-3:]
                    else:
                        masked_val = "****"
                    return masked_val
                return full
            redacted = re.sub(pattern, _mask, redacted)
        return redacted


def setup_logger(name: str = "AyushAI") -> logging.Logger:
    """Initializes and returns a configured logger instance."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    formatter = RedactingFormatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # File handler (5 MB max, 3 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    return logger

logger = setup_logger()
