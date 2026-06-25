from dataclasses import dataclass
from typing import Optional

@dataclass
class DownloadModel:
    id: str
    url: str
    filename: str
    status: str = "pending"
    size: int = 0
    downloaded: int = 0
    speed: float = 0.0
    eta: float = 0.0
    direct_url: Optional[str] = None
