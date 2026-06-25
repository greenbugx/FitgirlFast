from dataclasses import dataclass

@dataclass
class SettingsModel:
    download_folder: str
    max_concurrent: int
    auto_extract: bool
    delete_after: bool
