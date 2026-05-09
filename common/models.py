#common/models.py
from dataclasses import dataclass
@dataclass
class Request:
    def __init__(self, id, query, callback=None):
        self.id = id
        self.query = query
        self.callback = callback
        self.assigned_worker_id = None
        self.excluded_worker_ids = set()
        self.attempt = 0
@dataclass
class Response:
    id: int
    result: str
    latency: float
    worker_id: int = None
    status: str = "OK"
    error: str = None
