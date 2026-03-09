import logging
import json
from datetime import datetime


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "level": record.levelname.lower(),
            "service": getattr(record, "service", "web-app"),
            "message": record.getMessage(),
            "time": datetime.utcnow().isoformat()
        }
        return json.dumps(log_record)


def get_logger(service_name: str):
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = JsonFormatter()
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    def inject_service(record):
        record.service = service_name
        return True

    logger.addFilter(inject_service)

    return logger