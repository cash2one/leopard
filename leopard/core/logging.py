import logging.config

from leopard.core.config import get_config

logging_config = get_config(__name__)


def setup_logging():
    logging.config.dictConfig(logging_config)
