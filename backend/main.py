from backend.core.events import EventBus
from backend.core.config_manager import ConfigManager
from backend.core.pause_manager import PauseManager
from backend.core.cancel_manager import CancelManager
from backend.core.stats_manager import StatsManager
from backend.core.session_manager import SessionManager
from backend.core.extraction_manager import ExtractionManager
from backend.core.queue_manager import QueueManager
from backend.core.download_manager import DownloadManager

class BackendApp:
    def __init__(self):
        self.event_bus = EventBus()
        self.config_manager = ConfigManager()
        self.pause_manager = PauseManager(self.event_bus)
        self.cancel_manager = CancelManager(self.event_bus)
        self.stats_manager = StatsManager(self.event_bus)
        self.session_manager = SessionManager(self.event_bus)
        self.extraction_manager = ExtractionManager(self.event_bus)
        self.queue_manager = QueueManager(self.event_bus, self.config_manager)
        
        self.download_manager = DownloadManager(
            self.queue_manager,
            self.stats_manager,
            self.session_manager,
            self.extraction_manager,
            self.config_manager,
            self.pause_manager,
            self.cancel_manager,
            self.event_bus
        )
        
        self._setup_event_listeners()
        
    def _setup_event_listeners(self):
        def on_status(msg): print(f"[STATUS] {msg}")
        def on_completed(url): print(f"[DONE] {url}")
        def on_failed(url, err): print(f"[FAILED] {url} - {err}")
        def on_progress(url, done, total, speed, eta): pass # Silent to avoid spam
        
        self.event_bus.status_changed.connect(on_status)
        self.event_bus.download_completed.connect(on_completed)
        self.event_bus.download_failed.connect(on_failed)
        self.event_bus.download_progress.connect(on_progress)
        
    def start_download(self, urls, folder):
        self.download_manager.start_downloads(urls, folder)
