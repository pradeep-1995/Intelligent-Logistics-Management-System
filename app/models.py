from pydantic import BaseModel
from typing import List

class Order(BaseModel):
    id: int
    delivery_latitude: float
    delivery_longitude: float
    weight: int

class Route(BaseModel):
    vehicle_id: int
    route: List[int]

class Metrics(BaseModel):
    total_orders: int
    total_distance: float
    average_delivery_time: float