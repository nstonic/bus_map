import logging
import time

from exceptiongroup import ExceptionGroup
from trio_websocket import HandshakeError, ConnectionClosed


def retry_on_connection_error(timeout: int = 5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            while True:
                try:
                    func(*args, **kwargs)
                except (
                        ExceptionGroup,
                        OSError,
                        HandshakeError,
                        ConnectionError,
                        ConnectionRefusedError,
                        ConnectionClosed
                ):
                    logging.warning('Cannot connect to server. Retying')
                    time.sleep(timeout)
                    continue
            return

        return wrapper

    return decorator
