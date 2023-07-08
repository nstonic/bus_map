import json
from functools import partial
from sys import stderr

import trio
from trio_websocket import serve_websocket, ConnectionClosed

buses = {}


async def talk_to_browser(request):
    ws = await request.accept()
    buses_data = []
    for bus_id, bus_data in buses.items():
        bus_data.update({'busId': bus_id})
        buses_data.append(bus_data)
    message = json.dumps({
        "msgType": "Buses",
        "buses": buses_data
    })
    try:
        await ws.send_message(
            message
        )
        await trio.sleep(1)
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)


async def get_busses(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            # print(message)
            bus_data = json.loads(message)
            bus_id = bus_data.pop('busId')
            buses[bus_id] = bus_data
        except ConnectionClosed:
            break


async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            partial(serve_websocket, get_busses, '127.0.0.1', 8080, ssl_context=None)
        )
        nursery.start_soon(
            partial(serve_websocket, talk_to_browser, '127.0.0.1', 8000, ssl_context=None)
        )


trio.run(main)
