from dataclasses import dataclass, field
from typing import Dict
import logging_loki
import logging


@dataclass
class LokiConfig:
    url: str
    tags: Dict[str, str] = field(default_factory=lambda: {"application": "mogger"})
    username: str = None
    password: str = None


class LokiLogger:
    def __init__(self, config: LokiConfig):
        if config.username and config.password:
            auth = (config.username, config.password)
        else:
            auth = None

        loki_handler = logging_loki.LokiHandler(
            url=config.url,
            tags=config.tags,
            auth=auth,
            version="1",
            headers={
                "X-Scope-OrgID": "mogger-user"
            }
        )
        self.__logger = logging.getLogger("mogger")
        self.__logger.addHandler(loki_handler)

    def info(self, message: str, extra: Dict = {}):
        self.__logger.info(message, extra=extra)

    def warning(self, message: str, extra: Dict = {}):
        self.__logger.warning(message, extra=extra)

    def error(self, message: str, extra: Dict = {}):
        self.__logger.error(message, extra=extra)

    def critical(self, message: str, extra: Dict = {}):
        self.__logger.critical(message, extra=extra)

    def debug(self, message: str, extra: Dict = {}):
        self.__logger.debug(message, extra=extra)