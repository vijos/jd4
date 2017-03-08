from logging import getLogger
from logging.config import dictConfig

dictConfig({
    'version': 1,
    'handlers': {
      'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'colored',
      },
    },
    'formatters': {
      'colored': {
        '()': 'colorlog.ColoredFormatter',
        'format': '%(log_color)s[%(levelname).1s '
                  '%(asctime)s %(module)s:%(lineno)d]%(reset)s %(message)s',
        'datefmt': '%y%m%d %H:%M:%S'
      }
    },
    'root': {
      'level': 'DEBUG',
      'handlers': ['console'],
    },
    'disable_existing_loggers': False,
})

logger = getLogger(__name__)
