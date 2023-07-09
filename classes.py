import json


class Bus:
    _instances = {}

    def __new__(cls, *args, **kwargs):
        """
        Запрещаем создание экземпляров с одинаковыми bus_id.
        Заодно получаем перечень всех экземпляров.
        """
        bus_id = kwargs.get('bus_id', args[0])
        try:
            instance = cls._instances[bus_id]
        except KeyError:
            instance = super().__new__(cls)
            cls._instances[bus_id] = instance
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

    @classmethod
    def get_all_buses(cls):
        return cls._instances.values()

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


class WindowBounds:

    def __init__(
            self,
            east_lng: float,
            north_lat: float,
            south_lat: float,
            west_lng: float,
    ):
        """
        Немного расширим границы окна, чтобы автобусы уходили за его пределы и приходили от туда,
        а не исчезали и появлялись
        """
        horizontal_window_size = east_lng - west_lng
        vertical_window_size = north_lat - south_lat
        self.south_border = south_lat - vertical_window_size / 2
        self.north_border = north_lat + vertical_window_size / 2
        self.west_border = west_lng - horizontal_window_size / 2
        self.east_border = east_lng + horizontal_window_size / 2

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
            self.south_border < bus.lat < self.north_border,
            self.west_border < bus.lng < self.east_border
        ])
