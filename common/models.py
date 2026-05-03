#common/models.py
from dataclasses import dataclass
@dataclass
class Request:
    def __init__(self, id, query, callback=None):
        self.id = id
        self.query = query
        self.callback = callback
@dataclass
class Response:
    id: int
    result: str
    latency: float