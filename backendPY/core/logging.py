import logging
import sys
from core.config import settings

def setup_logging():
    log_level = logging.DEBUG if settings.APP_ENV == "development" else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress verbose loggers if needed
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    logger = logging.getLogger(settings.APP_NAME)
    logger.info(f"Logging initialized in {settings.APP_ENV} mode.")

setup_logging()
logger = logging.getLogger(settings.APP_NAME)
