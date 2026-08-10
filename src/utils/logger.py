import sys
from loguru import logger
from src.config.settings import settings


def setup_logger():
    logger.remove()
    
    # Console output
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )
    
    # File logging
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="7 days",
        level=settings.LOG_LEVEL,
        encoding="utf-8",
        enqueue=True,
    )

setup_logger()
export_logger = logger
