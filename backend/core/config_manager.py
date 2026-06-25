import os
import json
from backend.models.settings import SettingsModel

CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.fitgirlfast_config.json')

class ConfigManager:
    def __init__(self):
        self.settings = SettingsModel(
            download_folder=os.path.expanduser("~/Downloads"),
            max_concurrent=3,
            auto_extract=False,
            delete_after=False
        )
        self.load_config()
        
    def load_config(self):
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            self.settings.download_folder = cfg.get('download_folder', self.settings.download_folder)
            self.settings.max_concurrent = cfg.get('max_concurrent', self.settings.max_concurrent)
            self.settings.auto_extract = cfg.get('auto_extract', self.settings.auto_extract)
            self.settings.delete_after = cfg.get('delete_after', self.settings.delete_after)
        except Exception as e:
            print(f"[CONFIG] Failed to load config: {e}")
            
    def save_config(self):
        cfg = {
            'version': 1,
            'download_folder': self.settings.download_folder,
            'max_concurrent': self.settings.max_concurrent,
            'auto_extract': self.settings.auto_extract,
            'delete_after': self.settings.delete_after
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            print(f"[CONFIG] Failed to save config: {e}")
