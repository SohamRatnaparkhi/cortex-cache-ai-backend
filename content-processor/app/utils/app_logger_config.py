import logging

TOKEN_USAGE_LEVEL = 5
logging.addLevelName(TOKEN_USAGE_LEVEL, 'TOKEN_USAGE')

# Define log colors
LOG_COLORS = {
    'DEBUG': '\033[94m',     # Blue
    'INFO': '\033[92m',      # Green
    'WARNING': '\033[93m',   # Yellow
    'ERROR': '\033[91m',     # Red
    'CRITICAL': '\033[95m',  # Magenta
    'TOKEN_USAGE': '\033[96m',  # Cyan
}
RESET_COLOR = '\033[0m'


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_fmt = LOG_COLORS.get(
            record.levelname, '') + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + RESET_COLOR
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with custom formatter
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(ColoredFormatter())

# Add handler to logger
logger.addHandler(ch)
