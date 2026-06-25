from backend.models.download import DownloadModel
import time

class StatsManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.session_start = 0.0
        self.total_bytes = 0
        self.downloads = {}
        
    def init_session(self, items):
        self.session_start = time.monotonic()
        self.total_bytes = 0
        self.downloads.clear()
        
    def init_file(self, id: str, url: str, filename: str):
        self.downloads[id] = DownloadModel(id=id, url=url, filename=filename)
        
    def update_progress(self, id: str, chunk_len: int, total: int, done: int, speed: float, eta: float):
        self.total_bytes += chunk_len
        dl = self.downloads.get(id)
        if dl:
            dl.size = total
            dl.downloaded = done
            dl.speed = speed
            dl.eta = eta
            dl.status = 'active'
        self.event_bus.download_progress.emit(id, done, total, speed, eta)
        self.event_bus.stats_updated.emit(self.get_global_stats())
        
    def mark_status(self, id: str, status: str):
        dl = self.downloads.get(id)
        if dl:
            dl.status = status
            dl.speed = 0.0
            dl.eta = 0.0
        self.event_bus.status_changed.emit(f"Download {id} is now {status}")
        self.event_bus.stats_updated.emit(self.get_global_stats())
        
    def get_global_stats(self):
        start = self.session_start
        elapsed = time.monotonic() - start if start else 0
        total_mb = self.total_bytes / 1048576
        avg_speed = self.total_bytes / elapsed / 1048576 if elapsed > 0.5 else 0
        
        done_c = sum(1 for d in self.downloads.values() if d.status == 'done')
        failed_c = sum(1 for d in self.downloads.values() if d.status in ('error', 'cancelled'))
        pending_c = sum(1 for d in self.downloads.values() if d.status == 'pending')
        
        return {
            'elapsed': elapsed,
            'total_mb': total_mb,
            'avg_speed': avg_speed,
            'done_c': done_c,
            'failed_c': failed_c,
            'pending_c': pending_c
        }
