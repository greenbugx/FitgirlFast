from typing import Callable, Any

class Event:
    def __init__(self):
        self._listeners = []
    
    def connect(self, listener: Callable):
        if listener not in self._listeners:
            self._listeners.append(listener)
            
    def disconnect(self, listener: Callable):
        if listener in self._listeners:
            self._listeners.remove(listener)
            
    def emit(self, *args, **kwargs):
        for listener in self._listeners:
            try:
                listener(*args, **kwargs)
            except Exception as e:
                print(f"[Event Error] {e}")

class EventBus:
    def __init__(self):
        self.download_started = Event()
        self.download_progress = Event()
        self.download_paused = Event()
        self.download_resumed = Event()
        self.download_completed = Event()
        self.download_failed = Event()
        self.download_cancelled = Event()
        self.status_changed = Event()
        self.stats_updated = Event()
