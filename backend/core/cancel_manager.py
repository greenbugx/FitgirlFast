import threading

class CancelManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.cancel_events = {}
        
    def init_file(self, id: str):
        self.cancel_events[id] = threading.Event()
        
    def cancel_one(self, id: str):
        ev = self.cancel_events.get(id)
        if ev:
            ev.set()
            self.event_bus.download_cancelled.emit(id)
            
    def cancel_all(self):
        for id, ev in self.cancel_events.items():
            ev.set()
            self.event_bus.download_cancelled.emit(id)
            
    def is_cancelled(self, id: str) -> bool:
        ev = self.cancel_events.get(id)
        return ev is not None and ev.is_set()
