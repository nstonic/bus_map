import json
from dataclasses import dataclass


class Bus:
    instances = []

    def __new__(cls, *args, **kwargs):
        """
        Запрещаем создание экземпляров с одинаковыми bus_id.
        Заодно получаем список всех экземпляров.
        """
        bus_id = kwargs.get('bus_id') or args[0]
        try:
            instance = next(filter(
                lambda bus: bus.bus_id == bus_id,
                cls.instances
            ))
        except StopIteration:
            instance = super().__new__(cls)
            cls.instances.append(instance)
        return instance

    def __init__(self, bus_id, route, lat, lng):
        self.bus_id = bus_id
        self.route = route
        self.lat = lat
        self.lng = lng

    @classmethod
    def parse_raw(cls, raw: str):
        bus_data = json.loads(raw)
        return cls(
            bus_id=bus_data['busId'],
            lat=bus_data['lat'],
            lng=bus_data['lng'],
            route=bus_data['route']
        )

    def to_dict(self):
        return {
            "busId": self.bus_id,
            "lat": self.lat,
            "lng": self.lng,
            "route": self.route
        }

    def __str__(self):
        return self.bus_id

    def __repr__(self):
        return str(self.bus_id)


@dataclass
class WindowBounds:
    east_lng: float
    north_lat: float
    south_lat: float
    west_lng: float

    @classmethod
    def parse_raw(cls, raw: str):
        bounds_data = json.loads(raw)
        return cls(
            east_lng=bounds_data['data']['east_lng'],
            north_lat=bounds_data['data']['north_lat'],
            south_lat=bounds_data['data']['south_lat'],
            west_lng=bounds_data['data']['west_lng'],
        )

    def is_inside(self, bus: Bus) -> bool:
        return all([
            self.south_lat < bus.lat < self.north_lat,
            self.west_lng < bus.lng < self.east_lng
        ])
