import json
import logging
from contextlib import suppress
from functools import partial
from typing import Optional

import click
import trio
from trio_websocket import serve_websocket, ConnectionClosed

from classes import Bus, WindowBounds
from errors import ParsingError

bus_dicts = list[dict]


async def listen_browser(ws) -> Optional[bus_dicts]:
    msg = await ws.get_message()
    try:
        bounds = WindowBounds.parse_raw(msg)
    except ParsingError as ex:
        error_msg = json.dumps(
            {'msgType': 'Errors', 'errors': str(ex)}
        )
        logging.debug(error_msg)
        await ws.send_message(error_msg)
        return
    logging.debug(f'New bounds {msg}')
    return [
        bus.to_dict()
        for bus in Bus.get_all_buses()
        if bounds.is_inside(bus)
    ]


async def talk_to_browser(request):
    ws = await request.accept()
    buses_inside_bounds = await listen_browser(ws)
    if buses_inside_bounds is not None:
        msg = json.dumps({
            "msgType": "Buses",
            "buses": buses_inside_bounds
        })
        logging.debug(f'Sending buses: {buses_inside_bounds}')
        await ws.send_message(msg)


async def get_buses(request):
    ws = await request.accept()
    while True:
        msg = await ws.get_message()
        try:
            bus = Bus.parse_raw(msg)
        except ParsingError as ex:
            error_msg = json.dumps(
                {'msgType': 'Errors', 'errors': str(ex)}
            )
            logging.debug(error_msg)
            await ws.send_message(error_msg)
            continue
        logging.debug(f'Receiving bus data for {bus.bus_id}')


async def run(services: list):
    async with trio.open_nursery() as nursery:
        for srv in services:
            nursery.start_soon(srv)


@click.command()
@click.option('--buses_port', default=8080, type=int,
              help='Порт для получения данных об автобусах')
@click.option('--browser_port', default=8000, type=int,
              help='Порт для отправки данных в браузер')
@click.option('--no-log', is_flag=True,
              help='Отключить логирование')
def main(
        buses_port: int,
        browser_port: int,
        no_log: bool,
        browser_host: str = '127.0.0.1',
        buses_host: str = '127.0.0.1',
):
    if no_log:
        logging.disable(logging.FATAL)

    buses_receiving_srv = partial(
        serve_websocket,
        get_buses,
        buses_host,
        buses_port,
        ssl_context=None
    )
    browser_talking_srv = partial(
        serve_websocket,
        talk_to_browser,
        browser_host,
        browser_port,
        ssl_context=None
    )
    with suppress(KeyboardInterrupt, ConnectionClosed):
        trio.run(run, [buses_receiving_srv, browser_talking_srv])


if __name__ == '__main__':
    main()
