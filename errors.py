import logging
import time
from types import NoneType
from typing import Any, NoReturn

from exceptiongroup import ExceptionGroup
from trio_websocket import HandshakeError, ConnectionClosed


def relaunch_on_disconnect(timeout: int = 5):
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


class ParsingError(Exception):
    pass


def check_input_bounds(bounds: dict, expected_data_structure: Any) -> NoReturn:
    try:
        data_cls = bounds.__class__
        assert data_cls is not NoneType, ['Missing bounds data']
        assert data_cls is dict, [f'Expected dict, not {data_cls.__name__}']
        assert bounds.get('msgType') == 'newBounds', ['Wrong msgType']
    except AssertionError as ex:
        raise ParsingError(str(ex))
    check_input_data(bounds.get('data'), expected_data_structure)


def check_input_data(data: dict, expected_data_structure: Any) -> NoReturn:
    expected_data_cls = expected_data_structure.__class__
    data_cls = data.__class__
    try:
        assert data_cls is not NoneType, ['Missing data']
        assert data_cls is expected_data_cls, [f'Expected {expected_data_cls.__name__}, not {data_cls.__name__}']
        errors = []
        for attr_name, attr_type in expected_data_structure.items():
            attr_cls = data.get(attr_name).__class__
            if attr_cls is NoneType:
                errors.append(f'Attribute {attr_name} required')
            elif attr_cls is not attr_type:
                errors.append(f'{attr_name} must be {attr_type.__name__}, not {attr_cls.__name__}')
                continue
        assert errors == [], errors
    except AssertionError as ex:
        raise ParsingError(str(ex))
