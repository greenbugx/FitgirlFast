import threading

class PauseManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.global_pause_event = threading.Event()
        self.global_pause_event.set()
        self.per_file_pause = {}
        
    def init_file(self, url: str):
        ev = threading.Event()
        ev.set()
        self.per_file_pause[url] = ev
        
    def toggle_pause(self):
        if self.global_pause_event.is_set():
            self.global_pause_event.clear()
            self.event_bus.status_changed.emit("Paused globally")
        else:
            self.global_pause_event.set()
            self.event_bus.status_changed.emit("Resumed globally")
            
    def toggle_pause_one(self, url: str):
        ev = self.per_file_pause.get(url)
        if not ev: return
        if ev.is_set():
            ev.clear()
            self.event_bus.download_paused.emit(url)
        else:
            ev.set()
            self.event_bus.download_resumed.emit(url)
            
    def wait(self, url: str):
        self.global_pause_event.wait()
        ev = self.per_file_pause.get(url)
        if ev: ev.wait()
