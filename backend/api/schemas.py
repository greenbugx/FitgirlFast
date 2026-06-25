from pydantic import BaseModel
from typing import List, Optional

class DownloadItem(BaseModel):
    type: str
    url: str

class DownloadRequest(BaseModel):
    items: List[DownloadItem]
    folder: Optional[str] = None

class SettingsUpdate(BaseModel):
    download_folder: Optional[str] = None
    max_concurrent: Optional[int] = None
    auto_extract: Optional[bool] = None
    delete_after: Optional[bool] = None
