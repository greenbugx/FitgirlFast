import threading
import uuid
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
        
    def start_downloads(self, items: list, folder: str):
        self.event_bus.status_changed.emit("Starting downloads...")
        self.stats_manager.init_session(items)
        
        q_items = []
        for item in items:
            dl_id = uuid.uuid4().hex[:8]
            fname = _sanitize_fname(item['url'].split('#')[-1] if '#' in item['url'] else item['url'].split('/')[-1])
            self.stats_manager.init_file(dl_id, item['url'], fname)
            self.pause_manager.init_file(dl_id)
            self.cancel_manager.init_file(dl_id)
            q_item = QueueItemModel(id=dl_id, type=item.get('type', 'http'), url=item['url'], folder=folder)
            q_items.append(q_item)
            
        self.session_manager.save_session(q_items, folder)
        
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
        dl_id = item.id
        url = item.url
        folder = item.folder
        if self.cancel_manager.is_cancelled(dl_id):
            self.stats_manager.mark_status(dl_id, 'cancelled')
            self.event_bus.download_cancelled.emit(dl_id)
            return
            
        self.event_bus.status_changed.emit(f"Resolving {url}...")
        
        def status_cb(msg):
            self.event_bus.status_changed.emit(f"[{dl_id}] {msg}")
            
        direct_url = url
        if item.type == 'privatebin':
            pass
        elif 'fuckingfast' in url:
            direct_url = resolve_download_url(url, status_cb=status_cb)
            
        if not direct_url:
            self.stats_manager.mark_status(dl_id, 'error')
            self.event_bus.download_failed.emit(dl_id, "Failed to resolve URL")
            return
            
        self.event_bus.download_started.emit(dl_id)
        
        try:
            self.http_downloader.download(dl_id, url, direct_url, folder)
            self.stats_manager.mark_status(dl_id, 'done')
            self.event_bus.download_completed.emit(dl_id)
            self.session_manager.update_session_progress(dl_id, 'done')
        except CancelledError:
            self.stats_manager.mark_status(dl_id, 'cancelled')
            self.event_bus.download_cancelled.emit(dl_id)
            self.session_manager.update_session_progress(dl_id, 'cancelled')
        except Exception as e:
            self.stats_manager.mark_status(dl_id, 'error')
            self.event_bus.download_failed.emit(dl_id, str(e))
            self.session_manager.update_session_progress(dl_id, 'error')
