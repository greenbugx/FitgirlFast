import threading
from backend.downloaders.http_downloader import HttpDownloader, CancelledError
from backend.resolvers.fuckingfast import resolve_download_url
from backend.utils.filename import _sanitize_fname
from backend.models.queue import QueueItemModel

class DownloadManager:
    def __init__(self, queue_manager, stats_manager, session_manager, extraction_manager, config_manager, pause_manager, cancel_manager, event_bus):
        self.queue_manager = queue_manager
        self.stats_manager = stats_manager
        self.session_manager = session_manager
        self.extraction_manager = extraction_manager
        self.config_manager = config_manager
        self.pause_manager = pause_manager
        self.cancel_manager = cancel_manager
        self.event_bus = event_bus
        
        self.http_downloader = HttpDownloader(pause_manager, cancel_manager, stats_manager, event_bus)
        
    def start_downloads(self, urls: list, folder: str):
        self.event_bus.status_changed.emit("Starting downloads...")
        self.stats_manager.init_session(urls)
        
        q_items = []
        for url in urls:
            fname = _sanitize_fname(url.split('#')[-1] if '#' in url else url.split('/')[-1])
            self.stats_manager.init_file(url, fname)
            self.pause_manager.init_file(url)
            self.cancel_manager.init_file(url)
            q_items.append(QueueItemModel(url=url, folder=folder))
            
        self.session_manager.save_session(urls, folder)
        
        self.queue_manager.set_items(q_items)
        self.queue_manager.start_workers(self._dl_worker)
            
        self.session_manager.clear_session()
        
        if self.config_manager.settings.auto_extract:
            self.event_bus.status_changed.emit("Extracting downloaded archives...")
            success = self.extraction_manager.run_extraction(folder, self.stats_manager.downloads, self.config_manager.settings.delete_after)
            if success:
                self.event_bus.status_changed.emit("All downloads finished and extracted!")
            else:
                self.event_bus.status_changed.emit("All downloads finished (Extraction skipped/failed).")
        else:
            self.event_bus.status_changed.emit("All downloads finished.")
            
    def _dl_worker(self, item: QueueItemModel):
        url = item.url
        folder = item.folder
        if self.cancel_manager.is_cancelled(url):
            self.stats_manager.mark_status(url, 'cancelled')
            self.event_bus.download_cancelled.emit(url)
            return
            
        self.event_bus.status_changed.emit(f"Resolving {url}...")
        
        def status_cb(msg):
            self.event_bus.status_changed.emit(f"[{url}] {msg}")
            
        direct_url = resolve_download_url(url, status_cb=status_cb)
        
        if not direct_url:
            self.stats_manager.mark_status(url, 'error')
            self.event_bus.download_failed.emit(url, "Failed to resolve URL")
            return
            
        self.event_bus.download_started.emit(url)
        
        try:
            self.http_downloader.download(url, direct_url, folder)
            self.stats_manager.mark_status(url, 'done')
            self.event_bus.download_completed.emit(url)
            self.session_manager.update_session_progress(url, 'done')
        except CancelledError:
            self.stats_manager.mark_status(url, 'cancelled')
            self.event_bus.download_cancelled.emit(url)
            self.session_manager.update_session_progress(url, 'cancelled')
        except Exception as e:
            self.stats_manager.mark_status(url, 'error')
            self.event_bus.download_failed.emit(url, str(e))
            self.session_manager.update_session_progress(url, 'error')
