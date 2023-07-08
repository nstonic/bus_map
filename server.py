import json
from functools import partial

import trio
from trio_websocket import serve_websocket, ConnectionClosed

from classes import Bus, WindowBounds


async def run(services: list):
    async with trio.open_nursery() as nursery:
        for srv in services:
            nursery.start_soon(srv)


async def listen_browser(ws):
    msg = await ws.get_message()
    bounds = WindowBounds.parse_raw(msg)
    return [
        bus.to_dict()
        for bus in Bus.instances
        if bounds.is_inside(bus)
    ]


async def talk_to_browser(request):
    ws = await request.accept()
    buses_inside_bounds = await listen_browser(ws)
    msg = json.dumps({
        "msgType": "Buses",
        "buses": buses_inside_bounds
    })
    await ws.send_message(msg)
    await trio.sleep(1)


async def get_buses(request):
    buses_ws = await request.accept()
    while True:
        try:
            msg = await buses_ws.get_message()
            Bus.parse_raw(msg)
        except ConnectionClosed:
            break


def main(
        buses_host: str = '127.0.0.1',
        buses_port: int = 8080,
        host: str = '127.0.0.1',
        port: int = 8000,
):
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
        host,
        port,
        ssl_context=None
    )
    trio.run(run, [buses_receiving_srv, browser_talking_srv])


if __name__ == '__main__':
    main()
