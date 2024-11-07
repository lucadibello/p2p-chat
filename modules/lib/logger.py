import datetime
import logging
import os
from logging.handlers import RotatingFileHandler


class Logger:
    _instance = None

    def __init__(self, name="app_logger", log_level=logging.INFO, log_file=None):
        """
        Initializes a logger with the specified name, level, and optional file handler.

        Parameters:
            - name (str): Name of the logger instance.
            - log_level (int): Logging level (e.g., logging.DEBUG, logging.INFO).
            - log_file (str): Optional path to a log file. If provided, logs will also be written to this file.
        """
        # Ensure that the logger is only initialized once
        if not hasattr(self, "logger"):
            self.logger = logging.getLogger(name)
            self.logger.setLevel(log_level)

            # Avoid adding multiple handlers if logger already has them
            if not self.logger.handlers:
                # Console handler
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(self._get_formatter())
                self.logger.addHandler(console_handler)

                # File handler (optional)
                if log_file:
                    # Ensure the directory exists
                    os.makedirs(os.path.dirname(log_file), exist_ok=True)

                    file_handler = RotatingFileHandler(
                        log_file, maxBytes=5 * 1024 * 1024, backupCount=3
                    )
                    file_handler.setFormatter(self._get_formatter())
                    self.logger.addHandler(file_handler)

    def _get_formatter(self):
        """Define the log format and return a formatter instance."""
        return logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    def get_logger(self):
        """Returns the logger instance."""
        return self.logger

    @staticmethod
    def generate_file_name(format: str = "%s.log"):
        """Generate a log file name based on the current date and time."""
        now = datetime.datetime.now()
        return format % now.strftime("%Y-%m-%d_%H-%M-%S")
