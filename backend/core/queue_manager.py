import threading

class QueueManager:
    def __init__(self, event_bus, config_manager):
        self.event_bus = event_bus
        self.config_manager = config_manager
        self.items = []
        
    def set_items(self, items):
        self.items = items
        
    def start_workers(self, worker_func):
        max_c = self.config_manager.settings.max_concurrent
        sem = threading.Semaphore(max_c)
        threads = []
        for item in self.items:
            t = threading.Thread(target=self._wrap_worker, args=(worker_func, item, sem), daemon=True)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
            
    def _wrap_worker(self, worker_func, item, sem):
        sem.acquire()
        try:
            worker_func(item)
        finally:
            sem.release()
