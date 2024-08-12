import logging
import os
import colorlog
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
PORT = os.getenv('PORT', 3000)


def configure_logging():
    log_format = (
        '%(log_color)s%(asctime)s | %(levelname)s | %(name)s | '
        '%(process)d | %(filename)s:%(lineno)d | %(funcName)s | %(message)s'
    )
    colorlog.basicConfig(level=LOG_LEVEL, format=log_format, log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    })
    logger = logging.getLogger(__name__)
    return logger
