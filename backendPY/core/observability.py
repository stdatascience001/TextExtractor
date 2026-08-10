import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

class StructuredJSONFormatter(logging.Formatter):
    """Formats Python logs into structured JSON strings for OpenSearch/Datadog collection."""
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

# Tracing Span Context Emulator
class Tracer:
    @staticmethod
    def start_span(name: str) -> Dict[str, Any]:
        return {
            "name": name,
            "start_time": time.time()
        }

    @staticmethod
    def end_span(span: Dict[str, Any]):
        duration = (time.time() - span["start_time"]) * 1000
        # Print structured metrics trace log
        logger = logging.getLogger("tracer")
        logger.info(f"Span: {span['name']} completed in {duration:.2f}ms")
