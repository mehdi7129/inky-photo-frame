"""Display management singleton with GPIO/SPI lifecycle handling."""

import logging
import threading
import atexit
import signal
import time as time_module
from functools import wraps

from inky_photo_frame.config import VERSION


class DisplayManager:
    """
    Singleton to manage Inky display with robust GPIO/SPI handling.
    Initializes once, cleans up only on exit.
    """
    _instance = None
    _display = None
    _initialized = False
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize display once at startup"""
        with self._lock:
            if self._initialized:
                return self._display

            logging.info(f'🚀 Inky Photo Frame v{VERSION}')
            logging.info('Initializing display...')

            try:
                from inky.auto import auto
                self._display = auto()
                self._initialized = True

                width, height = self._display.resolution
                logging.info(f'✅ Display initialized: {width}x{height}')

                # Register cleanup handlers
                atexit.register(self.cleanup)
                signal.signal(signal.SIGTERM, lambda s, f: self.cleanup())
                signal.signal(signal.SIGINT, lambda s, f: self.cleanup())

                return self._display

            except Exception as e:
                logging.error(f'❌ Failed to initialize display: {e}')
                raise

    def get_display(self):
        """Get the display instance (initializes if needed)"""
        if not self._initialized:
            return self.initialize()
        return self._display

    def cleanup(self):
        """Cleanup display resources on exit"""
        with self._lock:
            if self._initialized and self._display:
                try:
                    if hasattr(self._display, '_spi'):
                        self._display._spi.close()
                    logging.info('🧹 Display cleaned up properly')
                except Exception as e:
                    logging.warning(f'Cleanup warning: {e}')
                finally:
                    self._initialized = False
                    self._display = None


def retry_on_error(max_attempts=3, delay=1, backoff=2):
    """
    Decorator to retry operations on GPIO/SPI errors
    Uses exponential backoff for resilience
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    # Check if it's a recoverable error
                    is_recoverable = any(x in error_msg for x in [
                        'gpio', 'spi', 'pins', 'transport', 'endpoint', 'busy'
                    ])

                    if is_recoverable and attempt < max_attempts:
                        wait_time = delay * (backoff ** (attempt - 1))
                        logging.warning(f'⚠️ Attempt {attempt}/{max_attempts} failed: {e}')
                        logging.info(f'Retrying in {wait_time}s...')
                        time_module.sleep(wait_time)
                    else:
                        logging.error(f'❌ Operation failed after {attempt} attempts: {e}')
                        raise
            return None
        return wrapper
    return decorator
