import threading

class CancelManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.cancel_events = {}
        
    def init_file(self, url: str):
        self.cancel_events[url] = threading.Event()
        
    def cancel_one(self, url: str):
        ev = self.cancel_events.get(url)
        if ev:
            ev.set()
            self.event_bus.download_cancelled.emit(url)
            
    def cancel_all(self):
        for url, ev in self.cancel_events.items():
            ev.set()
            self.event_bus.download_cancelled.emit(url)
            
    def is_cancelled(self, url: str) -> bool:
        ev = self.cancel_events.get(url)
        return ev is not None and ev.is_set()
