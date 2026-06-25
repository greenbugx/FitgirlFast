from dataclasses import dataclass

@dataclass
class QueueItemModel:
    id: str
    type: str
    url: str
    folder: str
