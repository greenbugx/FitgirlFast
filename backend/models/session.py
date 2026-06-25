from dataclasses import dataclass
from typing import List, Dict

@dataclass
class SessionModel:
    folder: str
    urls: List[str]
    selected: List[int]
    file_status: Dict[str, str]
