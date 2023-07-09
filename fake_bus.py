import json
import logging
import os
import random
from contextlib import suppress
from itertools import cycle
from json import JSONDecodeError

import click
import trio
from trio import MemoryReceiveChannel

from trio_websocket import open_websocket_url

from errors import relaunch_on_disconnect


class FakeBusGenerator:

    def __init__(
            self,
            buses_per_route: int = 20,
            routes_number: int = 0,
            routes_dir: str = 'routes',
            server_address: str = 'ws://127.0.0.1:8080',
            emulator_id: str = None,
            refresh_timeout: int = 1,
            websockets_number: int = 3
    ):
        self.routes_dir = routes_dir
        self.routes_number = routes_number
        self.buses_per_route = buses_per_route
        self.send_channels = []
        self.receive_channels = []
        self.emulator_id = emulator_id
        self.server_address = server_address
        self.websockets_number = websockets_number
        self.refresh_timeout = refresh_timeout
        self.routes = []
        self._get_routes()

    @relaunch_on_disconnect(timeout=2)
    def run(self):
        trio.run(self.start_generate_buses)

    async def start_generate_buses(self):
        total_buses = len(self.routes) * self.buses_per_route
        logging.debug(f'Start sending {total_buses} busses to the server {self.server_address}')
        try:
            self._open_channels()
            async with trio.open_nursery() as nursery:
                for receive_channel in self.receive_channels:
                    nursery.start_soon(self._send_updates, receive_channel)
                for route_data in self.routes:
                    for bus_index in range(self.buses_per_route):
                        nursery.start_soon(self._run_bus, route_data, bus_index)
        finally:
            await self._close_channels()

    def _get_routes(self):
        routes = os.listdir(self.routes_dir)
        random.shuffle(routes)
        for route in routes:
            rout_file_path = os.path.join(self.routes_dir, route)
            with open(rout_file_path, encoding='utf8') as f:
                route_raw = f.read()
                try:
                    route_data = json.loads(route_raw)
                except JSONDecodeError:
                    logging.warning(f'Cannot read route data from {rout_file_path}')
                else:
                    if not self._routes_is_full:
                        self.routes.append(route_data)
                    else:
                        break

    @property
    def _routes_is_full(self) -> bool:
        if self.routes_number <= 0:
            return False
        else:
            return len(self.routes) >= self.routes_number

    def _open_channels(self):
        for _ in range(self.websockets_number):
            send_channel, receive_channel = trio.open_memory_channel(0)
            self.send_channels.append(send_channel)
            self.receive_channels.append(receive_channel)

    async def _close_channels(self):
        all_channels = self.receive_channels + self.send_channels
        for channel in all_channels:
            await channel.aclose()
        self.receive_channels = list()
        self.send_channels = list()

    async def _run_bus(self, route_data: dict, bus_index: int):
        send_channel = random.choice(self.send_channels)

        coordinates = route_data['coordinates']
        start_position = random.randint(0, len(coordinates) - 1)
        bus_route = coordinates[start_position:] + coordinates[:start_position]

        bus_progress = {
            'busId': self._get_bus_id(route_data['name'], bus_index),
            'route': route_data['name']
        }
        for position in cycle(bus_route):
            bus_progress['lat'], bus_progress['lng'] = position
            await send_channel.send(bus_progress)
            await trio.sleep(self.refresh_timeout)

    async def _send_updates(self, receive_channel: MemoryReceiveChannel):
        async with open_websocket_url(self.server_address) as ws:
            async for msg in receive_channel:
                await ws.send_message(
                    json.dumps(msg, ensure_ascii=False)
                )
                logging.debug('Sending buses')

    def _get_bus_id(self, route_name: str, bus_index: int) -> str:
        bus_id = f'{route_name}-{bus_index}'
        if self.emulator_id:
            bus_id = f'{self.emulator_id} - {bus_id}'
        return bus_id


@click.command()
@click.option('--server', default='ws://127.0.0.1:8080',
              help='Адрес сервера')
@click.option('--routes_dir', default='routes',
              help='Папка с json-ами маршрутов')
@click.option('--routes_number', type=int, default=0,
              help='Количество маршрутов')
@click.option('--buses_per_route', type=int, default=20,
              help='Количество автобусов на каждом маршруте')
@click.option('--websockets_number', type=int, default=3,
              help='Количество открытых веб-сокетов')
@click.option('--emulator_id',
              help='Префикс к busId на случай запуска нескольких экземпляров имитатора')
@click.option('--refresh_timeout', default=1,
              help='Задержка в обновлении координат сервера в секундах')
@click.option('--no-log', is_flag=True,
              help='Отключить логирование')
def main(
        server: str,
        routes_dir: str,
        routes_number: int,
        buses_per_route: int,
        websockets_number: int,
        emulator_id: str,
        refresh_timeout: int,
        no_log: bool
):
    if no_log:
        logging.disable(logging.FATAL)

    bus_generator = FakeBusGenerator(
        server_address=server,
        buses_per_route=buses_per_route,
        routes_dir=routes_dir,
        routes_number=routes_number,
        emulator_id=emulator_id,
        refresh_timeout=refresh_timeout,
        websockets_number=websockets_number
    )
    with suppress(KeyboardInterrupt):
        bus_generator.run()


if __name__ == '__main__':
    main()
